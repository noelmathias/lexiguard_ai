from fastapi import APIRouter, HTTPException
from models.schemas import QueryRequest, QueryResponse
from core.input_handler import process_input
from core.rag import rag_system
from core.agents import run_agent_pipeline
from core.guidance import process_guidance_from_pipeline, format_guidance_for_response
from core.scoring import compute_scores, format_scores_for_response
from core.guardrails import (
    precheck_query,
    apply_guardrails,
    build_blocked_response
)
from workspace.ws_index import WorkspaceIndexCache
from utils.logger import logger

router = APIRouter()

# Workspace memory cache
ws_cache = WorkspaceIndexCache(
    lambda: rag_system.embedder
)


# ─────────────────────────────────────────────
# EARLY PRECHECK HELPER
# ─────────────────────────────────────────────

def _early_precheck(query: str) -> dict:
    """
    Run guardrail precheck with minimal context —
    before any RAG or LLM work.
    Uses empty entities since extraction hasn't run yet.
    Intent is estimated from keyword signals only.
    """
    query_lower = query.lower()

    # Fast intent hint from keywords — no LLM needed
    if any(w in query_lower for w in ["evict", "landlord", "tenant", "rent", "deposit"]):
        estimated_intent = "tenant_rights"
    elif any(w in query_lower for w in ["fired", "employer", "employee", "salary", "terminate"]):
        estimated_intent = "employment_law"
    elif any(w in query_lower for w in ["arrest", "police", "fir", "criminal", "fraud"]):
        estimated_intent = "criminal_law"
    elif any(w in query_lower for w in ["contract", "clause", "agreement", "sign"]):
        estimated_intent = "contract_analysis"
    else:
        estimated_intent = "general_legal"

    # Empty entities — extraction hasn't run yet
    empty_entities = {
        "parties": [], "legal_concepts": [], "documents": [],
        "locations": [], "amounts": [], "dates": [], "actions": []
    }

    return precheck_query(
        query    = query,
        intent   = estimated_intent,
        entities = empty_entities
    )


# ─────────────────────────────────────────────
# BLOCKED RESPONSE BUILDER
# ─────────────────────────────────────────────

def _build_blocked_query_response(
    precheck:   dict,
    input_type: str = "plain_text"
) -> QueryResponse:
    """Build a complete QueryResponse for a blocked query."""
    return QueryResponse(
        answer     = build_blocked_response(precheck["block_reason"]),
        confidence = 0.0,
        risk_score = 0.0,
        sources    = [],
        input_type = input_type,
        intent     = None,
        entities   = None,
        guidance   = None,
        scores     = None,
        guardrails = {
            "status":             "blocked",
            "blocked":            True,
            "block_reason":       precheck["block_reason"],
            "warnings":           precheck["warnings"],
            "flags":              [],
            "flag_count":         0,
            "hallucination_risk": "low",
            "was_modified":       True,
            "patches_applied":    ["Query blocked before LLM call."],
            "patch_count":        1
        }
    )


# ─────────────────────────────────────────────
# WORKSPACE + GLOBAL RETRIEVAL
# ─────────────────────────────────────────────

def retrieve_with_workspace(
    query: str,
    workspace_id: str = None,
    top_k: int = 5
):

    global_result = rag_system.retrieve(
        query=query,
        top_k=top_k
    )

    if not workspace_id:
        return global_result

    ws_index = ws_cache.get(workspace_id)

    ws_chunks = ws_index.search(
        query=query,
        top_k=3
    )

    if not ws_chunks:
        return global_result

    seen   = set()
    merged = []

    for chunk in (
        ws_chunks + global_result["chunks"]
    ):

        cid = chunk.get(
            "chunk_id",
            chunk.get("text", "")[:50]
        )

        if cid not in seen:

            seen.add(cid)

            merged.append(chunk)

    merged = merged[:top_k]

    lines = [
        "=== RETRIEVED LEGAL CONTEXT ===\n"
    ]

    for i, chunk in enumerate(merged, 1):

        source = (
            "📁 Your Document"
            if chunk.get("source") == "workspace"
            else chunk.get("category", "")
        )

        lines.append(
            f"[Source {i}] "
            f"{source} — "
            f"{chunk.get('title','')}\n"
            f"{chunk['text']}\n"
        )

    return {
        **global_result,
        "chunks": merged,
        "context": "\n".join(lines)
    }


# ─────────────────────────────────────────────
# MAIN ROUTE
# ─────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """
    Full pipeline with pre-LLM guardrail enforcement.

    Execution order:
    1. Guardrails precheck
    2. Input processing
    3. RAG retrieval
    4. LLM agent pipeline
    5. Guidance processing
    6. Scoring
    7. Guardrails post-check
    8. Response
    """

    # ── STEP 1: PRE-LLM GUARDRAIL PRECHECK ───────────────

    try:
        precheck = _early_precheck(request.query)

    except Exception as e:

        logger.warning(
            f"[Guardrails] Precheck failed with error: {e} — continuing."
        )

        precheck = {
            "blocked": False,
            "safe": True,
            "warnings": [],
            "block_reason": ""
        }

    if precheck["blocked"]:

        logger.warning(
            f"[Guardrails] Precheck — blocked: True | "
            f"reason: {precheck['block_reason'][:80]}"
        )

        logger.info(
            "[Route] Skipping LLM + RAG due to guardrail block."
        )

        return _build_blocked_query_response(precheck)

    logger.info(
        f"[Guardrails] Precheck — blocked: False | "
        f"warnings: {len(precheck['warnings'])}"
    )

    # ── STEP 2: INPUT PROCESSING ──────────────────────────

    try:

        processed = process_input(
            text=request.query,
            chat_history=request.chat_history
        )

    except Exception as e:

        logger.error(f"Input processing failed: {e}")

        raise HTTPException(
            500,
            f"Input processing failed: {str(e)}"
        )

    # ── STEP 3: RAG RETRIEVAL ─────────────────────────────

    try:

        retrieval = retrieve_with_workspace(
            query=processed["query"],
            workspace_id=getattr(request, "workspace_id", None),
            top_k=5
        )

    except Exception as e:

        logger.error(f"RAG retrieval failed: {e}")

        raise HTTPException(
            503,
            f"Retrieval failed: {str(e)}"
        )

    # ── STEP 4: LLM AGENT PIPELINE ───────────────────────

    try:

        result = run_agent_pipeline(
            query        = request.query,
            context      = retrieval["context"],
            confidence   = retrieval["confidence"],
            chat_history = request.chat_history,
            chunks       = retrieval["chunks"]
        )

    except RuntimeError as e:

        logger.error(f"LLM pipeline error: {e}")

        raise HTTPException(503, str(e))

    except Exception as e:

        logger.error(f"Agent pipeline failed: {e}")

        raise HTTPException(500, str(e))

    # ── STEP 5: GUIDANCE PROCESSING ──────────────────────

    guidance_processed = process_guidance_from_pipeline(
        guidance_raw = result["guidance_raw"],
        intent       = result["intent"]
    )

    guidance = format_guidance_for_response(
        guidance_processed
    )

    # ── STEP 6: SCORING ───────────────────────────────────

    scores = compute_scores(
        query                = request.query,
        intent               = result["intent"],
        intent_confidence    = result["intent_confidence"],
        entities             = result["entities"],
        retrieval_confidence = retrieval["confidence"],
        retrieved_chunks     = retrieval["chunks"],
        guidance_raw         = result["guidance_raw"]
    )

    score_response = format_scores_for_response(scores)

    # ── STEP 7: GUARDRAILS POST-CHECK ────────────────────

    guard = apply_guardrails(
        query      = request.query,
        answer     = result["answer"],
        intent     = result["intent"],
        entities   = result["entities"],
        context    = retrieval["context"],
        confidence = scores["confidence_score"] / 100
    )

    guardrails_response = {
        "status":             guard["status"],
        "blocked":            False,
        "block_reason":       "",
        "warnings":           precheck["warnings"],
        "flags":              guard["flags"],
        "flag_count":         guard["flag_count"],
        "hallucination_risk": guard["hallucination_risk"],
        "was_modified":       guard["was_modified"],
        "patches_applied":    guard["patches_applied"],
        "patch_count":        guard["patch_count"]
    }

    # ── STEP 8: RESPONSE ──────────────────────────────────

    return QueryResponse(
        answer     = guard["patched_answer"],
        confidence = scores["confidence_score"] / 100,
        risk_score = scores["risk_score"],
        sources    = [s["title"] for s in result["sources"]],
        input_type = processed["input_type"],
        intent     = result["intent"],
        entities   = result["entities"],
        guidance   = guidance,
        scores     = score_response,
        guardrails = guardrails_response
    )
