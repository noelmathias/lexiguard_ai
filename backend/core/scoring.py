"""Phase 8 scoring."""
from typing import Dict, List, Optional
from utils.logger import logger


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Intent base risk — how inherently risky each legal domain is
INTENT_BASE_RISK = {
    "tenant_rights":       45,
    "contract_analysis":   40,
    "contract_comparison": 40,
    "consumer_rights":     35,
    "employment_law":      50,
    "criminal_law":        70,
    "legal_notice":        55,
    "document_generation": 30,
    "general_legal":       25
}

# High-risk keywords that escalate risk score
HIGH_RISK_KEYWORDS = [
    "eviction", "evict", "arrested", "arrest", "criminal",
    "fraud", "assault", "harassment", "terminate", "terminated",
    "fired", "lawsuit", "sue", "court", "illegal", "unlawful",
    "forfeiture", "forfeit", "penalty", "fine", "prison", "jail",
    "warrant", "restraining order", "injunction", "damages",
    "breach", "default", "non-payment", "withhold", "seized"
]

# Moderate-risk keywords
MEDIUM_RISK_KEYWORDS = [
    "dispute", "complaint", "refund", "deduction", "delay",
    "notice", "warning", "overdue", "unpaid", "violation",
    "restriction", "prohibited", "obligation", "liable", "liability",
    "non-refundable", "irrevocable", "waive", "surrender"
]

# Urgency modifiers
URGENCY_MULTIPLIERS = {
    "high":   1.3,
    "medium": 1.0,
    "low":    0.8
}

# Confidence signal weights
CONFIDENCE_WEIGHTS = {
    "retrieval_score":   0.35,   # how good RAG retrieval was
    "intent_confidence": 0.25,   # how sure the model was of intent
    "entity_coverage":   0.20,   # how many entities were found
    "context_length":    0.10,   # how much context was retrieved
    "query_clarity":     0.10    # how clear the query is
}


# ─────────────────────────────────────────────
# RISK SCORING
# ─────────────────────────────────────────────

def compute_risk_score(
    query:           str,
    intent:          str,
    entities:        Dict,
    guidance_raw:    Optional[Dict] = None,
    contract_analysis: Optional[Dict] = None
) -> Dict:
    """
    Compute a risk score (0–100) for the current legal situation.
    Combines:
    - Intent base risk
    - Keyword signals in query
    - Entity signals (amounts, actions)
    - Guidance urgency
    - Contract analysis results (if available)

    Returns a RiskResult dict.
    """
    logger.info("[Scoring] Computing risk score...")

    score      = 0.0
    breakdown  = {}
    flags      = []

    # ── Component 1: Intent base risk ──────────
    base = INTENT_BASE_RISK.get(intent, 25)
    score += base
    breakdown["intent_base"] = base

    # ── Component 2: Query keyword signals ─────
    query_lower   = query.lower()
    high_matches  = [k for k in HIGH_RISK_KEYWORDS  if k in query_lower]
    med_matches   = [k for k in MEDIUM_RISK_KEYWORDS if k in query_lower]

    keyword_score = (len(high_matches) * 8) + (len(med_matches) * 4)
    keyword_score = min(keyword_score, 30)   # cap at 30
    score        += keyword_score
    breakdown["keyword_signals"] = keyword_score

    if high_matches:
        flags.append(f"High-risk keywords detected: {', '.join(high_matches[:3])}")

    # ── Component 3: Entity signals ────────────
    entity_score = 0
    amounts      = entities.get("amounts", [])
    actions      = entities.get("actions", [])
    parties      = entities.get("parties", [])

    # Financial amounts increase risk
    if amounts:
        entity_score += min(len(amounts) * 5, 15)
        flags.append(f"Financial amounts involved: {', '.join(str(a) for a in amounts[:3])}")

    # Legal actions increase risk
    high_risk_actions = [
        "sue", "evict", "arrest", "terminate", "forfeit",
        "seize", "injunct", "restrain", "prosecute"
    ]
    action_hits = [
        a for a in actions
        if any(h in str(a).lower() for h in high_risk_actions)
    ]
    if action_hits:
        entity_score += min(len(action_hits) * 6, 18)
        flags.append(
            f"High-risk actions identified: "
            f"{', '.join(str(a) for a in action_hits[:3])}"
        )

    entity_score  = min(entity_score, 20)
    score        += entity_score
    breakdown["entity_signals"] = entity_score

    # ── Component 4: Guidance urgency ──────────
    if guidance_raw:
        urgency    = guidance_raw.get("urgency", "medium")
        multiplier = URGENCY_MULTIPLIERS.get(urgency, 1.0)
        before     = score
        score      = score * multiplier
        urgency_delta             = round(score - before, 1)
        breakdown["urgency_modifier"] = urgency_delta
        if urgency == "high":
            flags.append("Situation assessed as HIGH urgency.")

    # ── Component 5: Contract risk overlay ─────
    if contract_analysis:
        contract_score = contract_analysis.get("overall_risk_score", 0)
        # Blend contract score in at 30% weight
        contract_contribution = contract_score * 0.3
        score                += contract_contribution
        breakdown["contract_overlay"] = round(contract_contribution, 1)

        unfair_count = contract_analysis.get("unfair_count", 0)
        if unfair_count > 0:
            flags.append(
                f"Contract contains {unfair_count} 🚨 UNFAIR clause(s)."
            )

    # ── Clamp to 0–100 ─────────────────────────
    final_score = max(0, min(100, round(score)))

    # ── Label ──────────────────────────────────
    label, display, colour = _risk_label(final_score)

    logger.info(
        f"[Scoring] Risk score: {final_score} | "
        f"label: {label} | flags: {len(flags)}"
    )

    return {
        "risk_score":     final_score,
        "risk_label":     label,
        "risk_display":   display,
        "risk_colour":    colour,
        "breakdown":      breakdown,
        "flags":          flags,
        "flag_count":     len(flags)
    }


def _risk_label(score: int):
    """Map score to label, display string, colour."""
    if score >= 70:
        return "high",   "🔴 HIGH RISK",    "#ef4444"
    if score >= 40:
        return "medium", "🟡 MEDIUM RISK",  "#f59e0b"
    return     "low",    "🟢 LOW RISK",     "#22c55e"


# ─────────────────────────────────────────────
# CONFIDENCE SCORING
# ─────────────────────────────────────────────

def compute_confidence_score(
    retrieval_confidence: float,
    intent_confidence:    float,
    entities:             Dict,
    query:                str,
    retrieved_chunks:     Optional[List[Dict]] = None
) -> Dict:
    """
    Compute a confidence score (0–100) for the system's answer.
    Combines:
    - RAG retrieval quality
    - Intent detection confidence
    - Entity coverage
    - Context length (chunks retrieved)
    - Query clarity

    Returns a ConfidenceResult dict.
    """
    logger.info("[Scoring] Computing confidence score...")

    components = {}

    # ── Component 1: Retrieval score ───────────
    # Already 0.0–1.0 from RAG system
    retrieval_norm       = max(0.0, min(1.0, retrieval_confidence))
    components["retrieval_score"] = retrieval_norm

    # ── Component 2: Intent confidence ─────────
    intent_norm          = max(0.0, min(1.0, intent_confidence))
    components["intent_confidence"] = intent_norm

    # ── Component 3: Entity coverage ───────────
    # More entities = clearer, more specific query
    total_entities = sum(
        len(v) for v in entities.values()
        if isinstance(v, list)
    )
    # Normalise: 5+ entities = full score
    entity_norm          = min(total_entities / 5.0, 1.0)
    components["entity_coverage"] = entity_norm

    # ── Component 4: Context length ────────────
    # More retrieved chunks = more supporting context
    chunk_count          = len(retrieved_chunks) if retrieved_chunks else 0
    context_norm         = min(chunk_count / 5.0, 1.0)
    components["context_length"] = context_norm

    # ── Component 5: Query clarity ─────────────
    # Longer, more specific queries score higher
    word_count           = len(query.split())
    has_question_word    = any(
        w in query.lower()
        for w in ["what", "how", "when", "where", "why", "can", "is", "are", "do"]
    )
    has_legal_term       = any(
        t in query.lower()
        for t in [
            "contract", "lease", "evict", "sue", "rights", "penalty",
            "deposit", "termination", "breach", "notice", "FIR", "arrest"
        ]
    )
    clarity              = 0.0
    clarity             += min(word_count / 20.0, 0.5)  # up to 0.5 for length
    clarity             += 0.25 if has_question_word else 0.0
    clarity             += 0.25 if has_legal_term    else 0.0
    components["query_clarity"] = min(clarity, 1.0)

    # ── Weighted sum ───────────────────────────
    raw_score = sum(
        components[k] * CONFIDENCE_WEIGHTS[k]
        for k in CONFIDENCE_WEIGHTS
    )

    final_score = max(0, min(100, round(raw_score * 100)))

    # ── Label ──────────────────────────────────
    label, display, colour = _confidence_label(final_score)

    # ── Explanation ────────────────────────────
    explanation = _build_confidence_explanation(
        final_score, components, retrieved_chunks
    )

    logger.info(
        f"[Scoring] Confidence: {final_score} | label: {label}"
    )

    return {
        "confidence_score":   final_score,
        "confidence_label":   label,
        "confidence_display": display,
        "confidence_colour":  colour,
        "components":         {k: round(v, 3) for k, v in components.items()},
        "explanation":        explanation
    }


def _confidence_label(score: int):
    """Map score to label, display string, colour."""
    if score >= 70:
        return "high",   "🟢 HIGH CONFIDENCE",   "#22c55e"
    if score >= 40:
        return "medium", "🟡 MEDIUM CONFIDENCE",  "#f59e0b"
    return     "low",    "🔴 LOW CONFIDENCE",     "#ef4444"


def _build_confidence_explanation(
    score:      int,
    components: Dict,
    chunks:     Optional[List[Dict]]
) -> str:
    """Generate a plain-English explanation of the confidence score."""
    parts = []

    if components.get("retrieval_score", 0) >= 0.6:
        parts.append("Strong document retrieval.")
    elif components.get("retrieval_score", 0) >= 0.3:
        parts.append("Moderate document retrieval.")
    else:
        parts.append("Weak retrieval — limited supporting documents found.")

    if components.get("intent_confidence", 0) >= 0.7:
        parts.append("Query intent clearly identified.")
    else:
        parts.append("Query intent uncertain.")

    if components.get("entity_coverage", 0) >= 0.6:
        parts.append("Good entity coverage.")
    else:
        parts.append("Few entities extracted — query may be vague.")

    if score < 40:
        parts.append(
            "Low confidence — consider rephrasing your query "
            "with more specific legal terms."
        )

    return " ".join(parts)


# ─────────────────────────────────────────────
# COMBINED SCORER
# ─────────────────────────────────────────────

def compute_scores(
    query:                str,
    intent:               str,
    intent_confidence:    float,
    entities:             Dict,
    retrieval_confidence: float,
    retrieved_chunks:     Optional[List[Dict]]  = None,
    guidance_raw:         Optional[Dict]        = None,
    contract_analysis:    Optional[Dict]        = None
) -> Dict:
    """
    Master scorer — computes both risk and confidence in one call.
    Zero LLM calls. Returns combined ScoreResult dict.
    """
    risk       = compute_risk_score(
        query            = query,
        intent           = intent,
        entities         = entities,
        guidance_raw     = guidance_raw,
        contract_analysis= contract_analysis
    )

    confidence = compute_confidence_score(
        retrieval_confidence = retrieval_confidence,
        intent_confidence    = intent_confidence,
        entities             = entities,
        query                = query,
        retrieved_chunks     = retrieved_chunks
    )

    # ── Score interaction: low confidence dampens high risk display ──
    # If we're not sure about our answer, we should not alarm the user
    # with a high risk score — note it but don't override
    confidence_note = ""
    if (risk["risk_label"] == "high" and
            confidence["confidence_label"] == "low"):
        confidence_note = (
            "⚠️ Note: Risk score is high but confidence is low. "
            "Please provide more details for a more accurate assessment."
        )

    return {
        "risk":             risk,
        "confidence":       confidence,
        "confidence_note":  confidence_note,
        # Flat fields for easy API access
        "risk_score":       risk["risk_score"],
        "risk_display":     risk["risk_display"],
        "confidence_score": confidence["confidence_score"],
        "confidence_display": confidence["confidence_display"]
    }


# ─────────────────────────────────────────────
# SCORE FORMATTER
# ─────────────────────────────────────────────

def format_scores_for_response(scores: Dict) -> Dict:
    """
    Format the combined score result into a clean
    API-ready structure for the frontend.
    """
    risk       = scores["risk"]
    confidence = scores["confidence"]

    return {
        "risk": {
            "score":    risk["risk_score"],
            "label":    risk["risk_label"],
            "display":  risk["risk_display"],
            "colour":   risk["risk_colour"],
            "flags":    risk["flags"],
            "breakdown": risk["breakdown"]
        },
        "confidence": {
            "score":       confidence["confidence_score"],
            "label":       confidence["confidence_label"],
            "display":     confidence["confidence_display"],
            "colour":      confidence["confidence_colour"],
            "explanation": confidence["explanation"],
            "components":  confidence["components"]
        },
        "confidence_note": scores.get("confidence_note", ""),
        "summary": (
            f"Risk: {risk['risk_display']} ({risk['risk_score']}/100) | "
            f"Confidence: {confidence['confidence_display']} "
            f"({confidence['confidence_score']}/100)"
        )
    }