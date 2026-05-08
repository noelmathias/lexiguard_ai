import re
import json
from typing import Dict, List, Optional
from utils.logger import logger
from core.llm_provider import (
    call_llm,
    call_llm_for_json,
    safe_parse_json,
    normalise_intent,
    VALID_INTENTS,
    DEFAULT_INTENT
)


# ─────────────────────────────────────────────
# INTENT + ENTITY PROMPT  (Call 1 — small, reliable)
# ─────────────────────────────────────────────

def _build_analysis_prompt(query: str) -> str:
    """
    Tiny prompt for intent + entity + rewrite only.
    Schema is flat and minimal — 3B models complete this reliably.
    """
    intents = "|".join(sorted(VALID_INTENTS))
    return f"""Classify this legal query and extract key information.

QUERY: {query}

Return ONLY this JSON. No other text:
{{"intent":"{intents}","confidence":0.8,"entities":{{"parties":[],"legal_concepts":[],"amounts":[],"actions":[]}},"rewritten":"{query}"}}

Rules:
- intent must be exactly one of the options shown
- confidence is a number 0.0 to 1.0
- lists contain short strings only
- rewritten is the query as a precise legal question"""


# ─────────────────────────────────────────────
# LEGAL ANSWER PROMPT  (Call 2 — structured text, not nested JSON)
# ─────────────────────────────────────────────

def _build_answer_prompt(
    query:    str,
    intent:   str,
    entities: Dict,
    context:  str,
    chat_history: Optional[List[dict]] = None
) -> str:
    """
    Focused prompt for legal answer + guidance.
    Returns structured plain text with labelled sections.
    Plain text is far more reliable than nested JSON for small models.
    """
    history_block = ""
    if chat_history:
        turns = [
            f"{t.get('role','user').capitalize()}: "
            f"{t.get('content','').strip()}"
            for t in chat_history[-2:]
            if t.get("content", "").strip()
        ]
        if turns:
            history_block = "PRIOR CONVERSATION:\n" + "\n".join(turns) + "\n\n"

    # Summarise entities compactly
    entity_parts = []
    for k, v in entities.items():
        if isinstance(v, list) and v:
            entity_parts.append(f"{k}: {', '.join(str(i) for i in v[:3])}")
    entity_summary = "; ".join(entity_parts) if entity_parts else "none identified"

    return f"""You are a legal assistant. Answer this query using ONLY the context provided.
Never invent laws, cases, or amounts.
If context is insufficient, say so clearly.

{history_block}LEGAL DOMAIN: {intent.replace("_", " ").upper()}
ENTITIES: {entity_summary}

CONTEXT:
{context}

QUERY: {query}

Write your response using EXACTLY these section labels on their own lines:

ANALYSIS:
[2-3 sentences answering the query using context only]

RIGHTS:
[right 1]
[right 2]
[right 3]

STEPS:
1. [step 1]
2. [step 2]
3. [step 3]

DOCUMENTS:
[document 1]
[document 2]

URGENCY: [low or medium or high]
URGENCY_REASON: [one sentence]

CAUTION:
[one sentence recommending a qualified lawyer]"""


# ─────────────────────────────────────────────
# ANSWER PARSER  (structured text → dict)
# ─────────────────────────────────────────────

def _parse_answer_text(text: str) -> Dict:
    """
    Parse labelled-section plain text into a structured dict.
    Much more forgiving than JSON parsing — small models
    can always produce correctly labelled sections even when
    they cannot produce valid nested JSON.
    """
    def _extract_section(label: str, full_text: str) -> str:
        """Extract content between one label and the next."""
        pattern = rf"^{label}:\s*\n?(.*?)(?=\n[A-Z_]+:|$)"
        match   = re.search(pattern, full_text, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()
        # Also try inline: LABEL: value on same line
        inline = re.search(rf"^{label}:\s*(.+)$", full_text, re.MULTILINE)
        if inline:
            return inline.group(1).strip()
        return ""

    def _extract_list(label: str, full_text: str) -> List[str]:
        """Extract a section and split into list items."""
        raw = _extract_section(label, full_text)
        if not raw:
            return []
        lines = [
            re.sub(r"^\d+\.\s*", "", line).strip()   # remove "1. " prefix
            for line in raw.split("\n")
            if line.strip() and line.strip() != label
        ]
        return [l for l in lines if l]

    analysis  = _extract_section("ANALYSIS",       text)
    rights    = _extract_list("RIGHTS",             text)
    steps     = _extract_list("STEPS",              text)
    documents = _extract_list("DOCUMENTS",          text)
    urgency   = _extract_section("URGENCY",         text).lower().strip()
    urg_reason= _extract_section("URGENCY_REASON",  text)
    caution   = _extract_section("CAUTION",         text)

    # Fallbacks for missing sections
    if not analysis:
        # Try to use the whole text as analysis if no sections detected
        analysis = text[:500].strip() if text.strip() else \
            "Unable to generate analysis. Please consult a qualified lawyer."

    if urgency not in ("low", "medium", "high"):
        # Try to infer from text
        text_lower = text.lower()
        if any(w in text_lower for w in ["urgent", "immediately", "criminal", "arrest"]):
            urgency = "high"
        elif any(w in text_lower for w in ["soon", "promptly", "notice"]):
            urgency = "medium"
        else:
            urgency = "medium"

    if not caution:
        caution = "Please consult a qualified lawyer for advice specific to your situation."

    return {
        "analysis":     analysis,
        "rights":       rights   or ["Right to consult a qualified lawyer"],
        "steps":        steps    or ["Document your situation", "Consult a qualified lawyer"],
        "documents":    documents or ["All relevant documents for your situation"],
        "urgency":      urgency,
        "urgency_reason": urg_reason or "Urgency based on the legal situation described.",
        "time_limit_warning": "",
        "caution":      caution
    }


# ─────────────────────────────────────────────
# CALL 1 — ANALYSIS (intent + entities + rewrite)
# ─────────────────────────────────────────────

def _run_analysis(query: str) -> Dict:
    """
    Run the small intent/entity/rewrite prompt.
    Returns validated analysis dict.
    Falls back cleanly on any failure.
    """
    fallback = {
        "intent":     DEFAULT_INTENT,
        "confidence": 0.5,
        "entities": {
            "parties": [], "legal_concepts": [],
            "amounts": [], "actions": []
        },
        "rewritten": query
    }

    raw    = call_llm_for_json(
        prompt     = _build_analysis_prompt(query),
        fallback   = fallback,
        max_tokens = 300
    )

    # Normalise intent regardless of what model returned
    raw["intent"] = normalise_intent(raw.get("intent", DEFAULT_INTENT))

    # Normalise confidence
    try:
        conf = float(raw.get("confidence", 0.5))
        if conf > 1.0:
            conf = conf / 100.0
        raw["confidence"] = round(max(0.0, min(1.0, conf)), 3)
    except (TypeError, ValueError):
        raw["confidence"] = 0.5

    # Ensure entities has expected keys
    raw.setdefault("entities", {})
    for key in ["parties", "legal_concepts", "amounts", "actions"]:
        val = raw["entities"].get(key, [])
        if not isinstance(val, list):
            raw["entities"][key] = (
                [v.strip() for v in str(val).split(",") if v.strip()]
                if val else []
            )

    # Fill missing entity keys that the full pipeline expects
    for extra_key in ["documents", "locations", "dates"]:
        raw["entities"].setdefault(extra_key, [])

    # Rewritten query fallback
    rq = raw.get("rewritten", "")
    if not isinstance(rq, str) or not rq.strip():
        raw["rewritten"] = query

    logger.info(
        f"[Call 1] intent={raw['intent']} | "
        f"conf={raw['confidence']} | "
        f"entities={sum(len(v) for v in raw['entities'].values() if isinstance(v,list))}"
    )

    return raw


# ─────────────────────────────────────────────
# CALL 2 — LEGAL ANSWER + GUIDANCE
# ─────────────────────────────────────────────

def _run_answer(
    query:        str,
    intent:       str,
    entities:     Dict,
    context:      str,
    chat_history: Optional[List[dict]] = None
) -> Dict:
    """
    Run the focused legal answer prompt.
    Returns parsed answer + guidance dict.
    """
    prompt = _build_answer_prompt(
        query, intent, entities, context, chat_history
    )

    try:
        # Plain text — do not use expect_json
        raw_text = call_llm(
            prompt      = prompt,
            max_tokens  = 800,
            expect_json = False,
            retries     = 3
        )
        result = _parse_answer_text(raw_text)
        logger.info(
            f"[Call 2] urgency={result['urgency']} | "
            f"rights={len(result['rights'])} | "
            f"steps={len(result['steps'])}"
        )
        return result

    except Exception as e:
        logger.error(f"[Call 2] Failed: {e} — using text fallback.")
        return {
            "analysis":  "Unable to generate legal analysis. Consult a qualified lawyer.",
            "rights":    ["Right to consult a qualified lawyer"],
            "steps":     ["Document your situation", "Consult a qualified lawyer"],
            "documents": ["All relevant documents"],
            "urgency":   "medium",
            "urgency_reason":     "Unable to assess — consult a lawyer.",
            "time_limit_warning": "",
            "caution": "Please consult a qualified lawyer for advice specific to your situation."
        }


# ─────────────────────────────────────────────
# MASTER PIPELINE
# ─────────────────────────────────────────────

def run_agent_pipeline(
    query:        str,
    context:      str,
    confidence:   float,
    chat_history: Optional[List[dict]] = None,
    chunks:       Optional[List[Dict]] = None
) -> Dict:
    """
    Two-call pipeline optimised for small local models.

    Call 1 — tiny JSON prompt  → intent, entities, rewrite   (~300 tokens)
    Call 2 — structured text   → legal answer + guidance     (~800 tokens)

    External interface unchanged — returns identical dict shape.
    """
    logger.info("=" * 50)
    logger.info("PIPELINE STARTED (2-call split)")
    logger.info("=" * 50)

    # ── Call 1 ───────────────────────────────
    analysis        = _run_analysis(query)
    intent          = analysis["intent"]
    intent_conf     = analysis["confidence"]
    entities        = analysis["entities"]
    rewritten_query = analysis["rewritten"]

    # ── Call 2 ───────────────────────────────
    answer_data = _run_answer(
        query        = rewritten_query,
        intent       = intent,
        entities     = entities,
        context      = context,
        chat_history = chat_history
    )

    # ── Format answer as markdown ─────────────
    formatted_answer = (
        f"## Legal Analysis\n{answer_data['analysis']}\n\n"
        f"## Your Rights / Obligations\n"
        + "\n".join(f"- {r}" for r in answer_data["rights"]) +
        f"\n\n## Recommended Steps\n"
        + "\n".join(
            f"{i+1}. {s}"
            for i, s in enumerate(answer_data["steps"])
        ) +
        f"\n\n## Important Caution\n{answer_data['caution']}"
    )

    logger.info(
        f"PIPELINE COMPLETE — "
        f"intent: {intent} | "
        f"urgency: {answer_data['urgency']}"
    )

    return {
        "answer":            formatted_answer,
        "intent":            intent,
        "intent_confidence": intent_conf,
        "entities":          entities,
        "rewritten_query":   rewritten_query,
        "confidence":        confidence,
        "guidance_raw": {
            "rights":             answer_data["rights"],
            "steps":              answer_data["steps"],
            "documents":          answer_data["documents"],
            "urgency":            answer_data["urgency"],
            "urgency_reason":     answer_data["urgency_reason"],
            "time_limit_warning": answer_data["time_limit_warning"]
        },
        "sources": [
            {
                "title":    c.get("title", ""),
                "category": c.get("category", ""),
                "score":    c.get("relevance_score", 0.0)
            }
            for c in (chunks or [])
        ]
    }