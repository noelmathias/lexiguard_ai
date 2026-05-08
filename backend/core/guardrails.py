"""Phase 9 guardrails."""
import re
from typing import Dict, List, Optional, Tuple
from utils.logger import logger


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Patterns that indicate fabricated legal citations
FAKE_CITATION_PATTERNS = [
    # Fabricated case names
    r'\b[A-Z][a-z]+ v\.? [A-Z][a-z]+,?\s*\d{3,4}\b',
    # Fabricated statute numbers
    r'\bSection\s+\d+[A-Z]?\s+of\s+the\s+[A-Z][a-zA-Z\s]+Act\b',
    r'\b[A-Z][a-zA-Z\s]+Act,?\s*(19|20)\d{2}\b',
    # Fabricated US Code citations
    r'\b\d+\s+U\.S\.C\.?\s+§?\s*\d+\b',
    # Fabricated CFR citations
    r'\b\d+\s+C\.F\.R\.?\s+§?\s*\d+\b',
    # Fabricated case reporters
    r'\b\d+\s+[A-Z][a-z]*\.?\s*\d[a-z]*\s+\d+\b',
]

# Phrases that indicate the model is making things up
HALLUCINATION_PHRASES = [
    "as established in the landmark case",
    "according to the supreme court ruling",
    "the law clearly states that",
    "it is a well-established legal principle that",
    "as per section",
    "under article",
    "the statute explicitly states",
    "the federal law requires",
    "the act mandates",
    "case law confirms",
    "judicial precedent establishes",
    "the court held in",
    "per the ruling in",
    "it is illegal under",
    "you are legally entitled to exactly",
    "the exact penalty is",
    "the specific amount required by law is",
]

# Uncertainty markers the model should use — we check for their absence
UNCERTAINTY_MARKERS = [
    "typically", "generally", "usually", "often", "may", "might",
    "could", "consult", "verify", "qualified lawyer", "legal advice",
    "jurisdiction", "varies", "depending", "recommend", "suggest",
    "it is advisable", "in most cases", "as a general rule"
]

# Absolute claim patterns — red flags for overconfident statements
ABSOLUTE_CLAIM_PATTERNS = [
    r'\byou (will|shall|must) (definitely|certainly|absolutely)\b',
    r'\bguaranteed (to|that)\b',
    r'\b100%\s*(certain|sure|guaranteed|legal|illegal)\b',
    r'\bno (court|judge|lawyer) (will|can|would)\b',
    r'\byou (cannot|can never) lose\b',
    r'\bthis is definitely (legal|illegal)\b',
    r'\bwithout (any|a) doubt\b',
    r'\bthe law is clear(ly)?\b',
]

# Context insufficiency signals — when retrieved context is too thin
CONTEXT_INSUFFICIENCY_PHRASES = [
    "i don't have information",
    "i cannot find",
    "no information available",
    "outside my knowledge",
    "i'm not sure about",
    "i don't know",
    "unable to find",
    "not in the provided context",
    "the context does not",
    "based on the context provided, i cannot",
]

# Topics that always require professional advice disclaimers
HIGH_STAKES_INTENTS = {
    "criminal_law",
    "employment_law",
    "legal_notice"
}

# Standard disclaimer to append when missing
STANDARD_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Important:** This information is for general guidance only "
    "and does not constitute legal advice. Laws vary by jurisdiction. "
    "Always consult a qualified lawyer for advice specific to your situation."
)

# Short disclaimer for injection into thin answers
SHORT_DISCLAIMER = (
    " Please consult a qualified lawyer for advice specific to your situation."
)


# ─────────────────────────────────────────────
# PRE-FLIGHT CHECKS (run before LLM call)
# ─────────────────────────────────────────────

def precheck_query(
    query:   str,
    intent:  str,
    entities: Dict
) -> Dict:
    """
    Run before the LLM call.
    Validates the query is appropriate and safe to process.

    Returns:
    {
        "safe":     bool,
        "warnings": List[str],
        "blocked":  bool,
        "block_reason": str
    }
    """
    warnings    = []
    blocked     = False
    block_reason = ""

    query_lower = query.lower()

    # Block 1: Extremely short queries
    if len(query.split()) < 3:
        warnings.append(
            "Query is very short — results may be vague. "
            "Add more detail for better guidance."
        )

    # Block 2: Requests for specific legal loopholes
    loophole_patterns = [
        "how to avoid", "how to get away with", "how to hide",
        "without getting caught", "bypass the law", "illegal but",
        "loophole for", "cheat the system"
    ]
    if any(p in query_lower for p in loophole_patterns):
        blocked      = True
        block_reason = (
            "This query appears to seek ways to circumvent legal obligations. "
            "This system provides legal guidance, not advice on evading the law."
        )

    # Block 3: Requests for specific legal advice about ongoing criminal acts
    criminal_active = [
        "i am currently committing",
        "i am planning to commit",
        "how to commit",
        "how do i commit"
    ]
    if any(p in query_lower for p in criminal_active):
        blocked      = True
        block_reason = (
            "This system cannot provide guidance on committing illegal acts."
        )

    # Warning: No entities found for complex query
    total_entities = sum(
        len(v) for v in entities.values()
        if isinstance(v, list)
    )
    if len(query.split()) > 15 and total_entities == 0:
        warnings.append(
            "No specific legal entities were detected in your query. "
            "Results may be general rather than specific to your situation."
        )

    # Warning: High-stakes domain
    if intent in HIGH_STAKES_INTENTS:
        warnings.append(
            f"This query involves {intent.replace('_', ' ')} — "
            "a high-stakes legal area. Professional legal advice is strongly recommended."
        )

    logger.info(
        f"[Guardrails] Precheck — blocked: {blocked} | "
        f"warnings: {len(warnings)}"
    )

    return {
        "safe":          not blocked,
        "warnings":      warnings,
        "blocked":       blocked,
        "block_reason":  block_reason
    }


# ─────────────────────────────────────────────
# POST-FLIGHT CHECKS (run after LLM response)
# ─────────────────────────────────────────────

def _check_fake_citations(text: str) -> List[str]:
    """Detect potentially fabricated legal citations."""
    found = []
    for pattern in FAKE_CITATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            found.append(f"Possible fabricated citation: '{match}'")
    return found


def _check_hallucination_phrases(text: str) -> List[str]:
    """Detect phrases associated with overconfident/fabricated claims."""
    text_lower = text.lower()
    found = []
    for phrase in HALLUCINATION_PHRASES:
        if phrase in text_lower:
            found.append(f"Overconfident claim detected: '...{phrase}...'")
    return found


def _check_absolute_claims(text: str) -> List[str]:
    """Detect absolute guarantee-style claims."""
    found = []
    for pattern in ABSOLUTE_CLAIM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            found.append(f"Absolute claim detected: '{match}'")
    return found


def _check_uncertainty_markers(
    text:   str,
    intent: str
) -> List[str]:
    """
    For high-stakes intents, verify uncertainty markers are present.
    If answer sounds too definitive, flag it.
    """
    warnings = []
    if intent not in HIGH_STAKES_INTENTS:
        return warnings

    text_lower    = text.lower()
    marker_count  = sum(
        1 for m in UNCERTAINTY_MARKERS
        if m in text_lower
    )

    if marker_count < 2 and len(text.split()) > 50:
        warnings.append(
            "Response may be overly definitive for a high-stakes legal topic. "
            "Uncertainty markers are sparse."
        )
    return warnings


def _check_context_usage(
    answer:  str,
    context: str
) -> List[str]:
    """
    Check if the answer is grounded in the retrieved context
    or appears to be fabricated independently.
    """
    warnings = []
    answer_lower = answer.lower()

    # Check if answer acknowledges context insufficiency appropriately
    for phrase in CONTEXT_INSUFFICIENCY_PHRASES:
        if phrase in answer_lower:
            warnings.append(
                "Answer acknowledges limited context — "
                "response may be incomplete."
            )
            break

    # Check if context is very short (thin retrieval)
    context_words = len(context.split())
    if context_words < 50:
        warnings.append(
            "Retrieved context is thin — answer may lack supporting evidence. "
            "Consider rephrasing your query."
        )

    return warnings


def _check_disclaimer_presence(
    answer: str,
    intent: str
) -> bool:
    """
    Check if the answer contains a disclaimer.
    Returns True if disclaimer is present.
    """
    disclaimer_markers = [
        "consult", "lawyer", "legal advice", "qualified",
        "jurisdiction", "professional", "not legal advice",
        "verify", "attorney"
    ]
    answer_lower = answer.lower()
    return any(m in answer_lower for m in disclaimer_markers)


# ─────────────────────────────────────────────
# ANSWER PATCHER
# ─────────────────────────────────────────────

def _patch_answer(
    answer:           str,
    intent:           str,
    hallucination_flags: List[str],
    missing_disclaimer:  bool
) -> Tuple[str, List[str]]:
    """
    Patch the answer by:
    1. Adding disclaimer if missing
    2. Injecting uncertainty language around flagged phrases
    3. Adding caution header if hallucination risk is high

    Returns (patched_answer, list_of_patches_applied).
    """
    patches  = []
    patched  = answer

    # Patch 1: Add disclaimer if missing
    if missing_disclaimer:
        patched += STANDARD_DISCLAIMER
        patches.append("Added standard legal disclaimer.")

    # Patch 2: High hallucination risk — add prominent caution block
    if len(hallucination_flags) >= 2:
        caution_block = (
            "\n\n> ⚠️ **Verification Required:** Some statements in this "
            "response reference specific legal provisions. Please verify "
            "all cited laws, cases, and figures with a qualified lawyer "
            "before relying on them."
        )
        patched  = patched + caution_block
        patches.append(
            "Added verification caution block due to "
            "multiple hallucination risk flags."
        )

    # Patch 3: Soften absolute claims inline
    absolute_softeners = [
        (r'\byou will definitely\b',    "you may"),
        (r'\byou are guaranteed\b',     "you may be entitled"),
        (r'\bthis is definitely legal\b', "this may be legal"),
        (r'\bthis is definitely illegal\b', "this may be illegal"),
        (r'\b100% certain\b',           "generally considered"),
    ]
    for pattern, replacement in absolute_softeners:
        new = re.sub(pattern, replacement, patched, flags=re.IGNORECASE)
        if new != patched:
            patches.append(f"Softened absolute claim matching '{pattern}'.")
            patched = new

    return patched, patches


# ─────────────────────────────────────────────
# MASTER POST-CHECK
# ─────────────────────────────────────────────

def postcheck_answer(
    answer:     str,
    intent:     str,
    context:    str,
    confidence: float
) -> Dict:
    """
    Run after LLM response.
    Checks for hallucinations, missing disclaimers,
    absolute claims, and context grounding.

    Returns a GuardrailsResult dict with
    patched answer and all flags.
    """
    logger.info("[Guardrails] Running post-check...")

    all_flags       = []
    hallucination_flags = []

    # Check 1: fake citations
    citation_flags  = _check_fake_citations(answer)
    hallucination_flags.extend(citation_flags)
    all_flags.extend(citation_flags)

    # Check 2: hallucination phrases
    phrase_flags    = _check_hallucination_phrases(answer)
    hallucination_flags.extend(phrase_flags)
    all_flags.extend(phrase_flags)

    # Check 3: absolute claims
    absolute_flags  = _check_absolute_claims(answer)
    all_flags.extend(absolute_flags)

    # Check 4: uncertainty markers
    uncertainty_flags = _check_uncertainty_markers(answer, intent)
    all_flags.extend(uncertainty_flags)

    # Check 5: context grounding
    context_flags   = _check_context_usage(answer, context)
    all_flags.extend(context_flags)

    # Check 6: disclaimer presence
    has_disclaimer  = _check_disclaimer_presence(answer, intent)
    missing_disclaimer = (
        not has_disclaimer and
        intent in HIGH_STAKES_INTENTS
    )
    if missing_disclaimer:
        all_flags.append(
            "Disclaimer missing from high-stakes legal response."
        )

    # Compute hallucination risk level
    h_count = len(hallucination_flags)
    if h_count >= 3:
        hallucination_risk = "high"
    elif h_count >= 1:
        hallucination_risk = "medium"
    else:
        hallucination_risk = "low"

    # Low confidence + any flag = escalate
    if confidence < 0.4 and all_flags:
        hallucination_risk = max(
            hallucination_risk,
            "medium",
            key=lambda x: ["low","medium","high"].index(x)
        )

    # Patch answer
    patched_answer, patches_applied = _patch_answer(
        answer,
        intent,
        hallucination_flags,
        missing_disclaimer
    )

    # Compute overall pass/warn/fail
    if hallucination_risk == "high":
        guard_status = "warn"
    elif len(all_flags) > 3:
        guard_status = "warn"
    else:
        guard_status = "pass"

    logger.info(
        f"[Guardrails] Post-check done — "
        f"flags: {len(all_flags)} | "
        f"hallucination_risk: {hallucination_risk} | "
        f"status: {guard_status} | "
        f"patches: {len(patches_applied)}"
    )

    return {
        "status":              guard_status,
        "hallucination_risk":  hallucination_risk,
        "flags":               all_flags,
        "flag_count":          len(all_flags),
        "hallucination_flags": hallucination_flags,
        "patches_applied":     patches_applied,
        "patch_count":         len(patches_applied),
        "patched_answer":      patched_answer,
        "original_answer":     answer,
        "was_modified":        patched_answer != answer
    }


# ─────────────────────────────────────────────
# BLOCKED RESPONSE BUILDER
# ─────────────────────────────────────────────

def build_blocked_response(block_reason: str) -> str:
    """
    Build a safe response for blocked queries.
    """
    return (
        f"## Query Not Processed\n\n"
        f"{block_reason}\n\n"
        f"## What You Can Do\n\n"
        f"This system is designed to provide lawful legal guidance. "
        f"If you believe your query was blocked in error, please rephrase it "
        f"to focus on your legal rights and options.\n\n"
        f"For urgent legal matters, please consult a qualified lawyer directly."
    )


# ─────────────────────────────────────────────
# UNCERTAINTY INJECTOR
# ─────────────────────────────────────────────

def inject_uncertainty_flags(
    answer:     str,
    confidence: float,
    intent:     str
) -> Tuple[str, bool]:
    """
    If confidence is low, prepend an uncertainty notice to the answer.
    Returns (modified_answer, was_modified).
    """
    if confidence >= 0.5:
        return answer, False

    if confidence < 0.3:
        notice = (
            "> 🔍 **Low Confidence Notice:** The system has limited supporting "
            "information for this query. The following guidance is general and "
            "may not fully apply to your specific situation. "
            "Consulting a qualified lawyer is strongly advised.\n\n"
        )
    else:
        notice = (
            "> ℹ️ **Moderate Confidence Notice:** This response is based on "
            "partial information. Please verify details with a qualified lawyer.\n\n"
        )

    return notice + answer, True


# ─────────────────────────────────────────────
# MASTER GUARDRAILS FUNCTION
# ─────────────────────────────────────────────

def apply_guardrails(
    query:       str,
    answer:      str,
    intent:      str,
    entities:    Dict,
    context:     str,
    confidence:  float
) -> Dict:
    """
    Master guardrails function — runs full pre + post pipeline.

    Call this AFTER the LLM has already generated an answer.
    (Precheck is called separately before the LLM call.)

    Returns a GuardrailsResult dict with safe patched answer.
    """
    # Post-check
    post = postcheck_answer(
        answer     = answer,
        intent     = intent,
        context    = context,
        confidence = confidence
    )

    # Inject uncertainty if confidence is low
    final_answer, uncertainty_injected = inject_uncertainty_flags(
        answer     = post["patched_answer"],
        confidence = confidence,
        intent     = intent
    )

    if uncertainty_injected:
        post["patches_applied"].append(
            "Injected uncertainty notice due to low confidence score."
        )
        post["patch_count"] += 1
        post["was_modified"]  = True

    post["patched_answer"] = final_answer

    logger.info(
        f"[Guardrails] Complete — "
        f"status: {post['status']} | "
        f"modified: {post['was_modified']}"
    )

    return post