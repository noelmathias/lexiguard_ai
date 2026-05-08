"""Evaluation metrics for generated legal responses."""
import re
from typing import Dict, List, Optional
from utils.logger import logger


# ─────────────────────────────────────────────
# INTENT ACCURACY
# ─────────────────────────────────────────────

def score_intent(
    expected: Optional[str],
    actual:   Optional[str]
) -> Dict:
    """Score intent detection accuracy."""
    if expected is None:
        return {"score": 1.0, "passed": True, "detail": "No intent expected (blocked query)."}

    if actual is None:
        return {"score": 0.0, "passed": False, "detail": "No intent returned."}

    passed = expected.strip() == actual.strip()
    return {
        "score":  1.0 if passed else 0.0,
        "passed": passed,
        "detail": f"Expected '{expected}' | Got '{actual}'"
    }


# ─────────────────────────────────────────────
# KEYWORD COVERAGE
# ─────────────────────────────────────────────

def score_keyword_coverage(
    answer:            str,
    expected_keywords: List[str],
    forbidden_keywords: List[str]
) -> Dict:
    """
    Score how many expected keywords appear in the answer
    and penalise for forbidden keywords.
    """
    answer_lower = answer.lower()
    found        = [k for k in expected_keywords if k.lower() in answer_lower]
    forbidden    = [k for k in forbidden_keywords if k.lower() in answer_lower]

    coverage = (
        len(found) / len(expected_keywords)
        if expected_keywords else 1.0
    )
    penalty  = len(forbidden) * 0.2
    score    = max(0.0, min(1.0, coverage - penalty))

    return {
        "score":               round(score, 3),
        "passed":              score >= 0.5,
        "keywords_found":      found,
        "keywords_missing":    [k for k in expected_keywords if k not in found],
        "forbidden_found":     forbidden,
        "coverage_rate":       round(coverage, 3)
    }


# ─────────────────────────────────────────────
# DISCLAIMER CHECK
# ─────────────────────────────────────────────

def score_disclaimer(
    answer:   str,
    required: bool
) -> Dict:
    """Check if disclaimer is present when required."""
    if not required:
        return {
            "score": 1.0, "passed": True,
            "detail": "Disclaimer not required for this query type."
        }

    markers = [
        "consult", "lawyer", "legal advice", "qualified",
        "jurisdiction", "professional", "not legal advice",
        "verify", "attorney", "seek advice"
    ]
    answer_lower = answer.lower()
    found        = any(m in answer_lower for m in markers)

    return {
        "score":  1.0 if found else 0.0,
        "passed": found,
        "detail": "Disclaimer present." if found else "Disclaimer missing."
    }


# ─────────────────────────────────────────────
# CONFIDENCE RANGE CHECK
# ─────────────────────────────────────────────

def score_confidence(
    actual:  float,
    minimum: float
) -> Dict:
    """Check confidence score meets minimum threshold."""
    actual_pct = actual if actual <= 1.0 else actual / 100
    passed     = actual_pct >= minimum

    return {
        "score":  1.0 if passed else round(actual_pct / maximum(minimum, 0.01), 2),
        "passed": passed,
        "detail": f"Confidence {round(actual_pct, 3)} | Minimum {minimum}"
    }


def maximum(a, b):
    return a if a > b else b


# ─────────────────────────────────────────────
# RISK SCORE RANGE CHECK
# ─────────────────────────────────────────────

def score_risk_range(
    actual:    float,
    min_score: int,
    max_score: int
) -> Dict:
    """Check risk score falls within expected range."""
    passed = min_score <= actual <= max_score
    return {
        "score":  1.0 if passed else 0.0,
        "passed": passed,
        "detail": (
            f"Risk {actual} within [{min_score}–{max_score}]"
            if passed else
            f"Risk {actual} OUTSIDE [{min_score}–{max_score}]"
        )
    }


# ─────────────────────────────────────────────
# GUARDRAIL BLOCK CHECK
# ─────────────────────────────────────────────

def score_guardrail_block(
    guardrails:        Optional[Dict],
    should_be_blocked: bool
) -> Dict:
    """Check if guardrail correctly blocked or allowed a query."""
    if not should_be_blocked:
        return {
            "score": 1.0, "passed": True,
            "detail": "Block not expected — skipping."
        }

    if guardrails is None:
        return {
            "score": 0.0, "passed": False,
            "detail": "Guardrails missing from response."
        }

    was_blocked = guardrails.get("blocked", False)
    return {
        "score":  1.0 if was_blocked else 0.0,
        "passed": was_blocked,
        "detail": (
            "Query correctly blocked." if was_blocked
            else "Query was NOT blocked — GUARDRAIL FAILURE."
        )
    }


# ─────────────────────────────────────────────
# URGENCY CHECK
# ─────────────────────────────────────────────

def score_urgency(
    actual:   Optional[str],
    expected: List[str]
) -> Dict:
    """Check urgency level is within expected values."""
    if not expected or not actual:
        return {"score": 1.0, "passed": True, "detail": "Urgency not checked."}

    passed = actual.lower() in [e.lower() for e in expected]
    return {
        "score":  1.0 if passed else 0.5,
        "passed": passed,
        "detail": f"Urgency '{actual}' | Expected one of {expected}"
    }


# ─────────────────────────────────────────────
# ANSWER STRUCTURE CHECK
# ─────────────────────────────────────────────

def score_answer_structure(answer: str) -> Dict:
    """
    Check if answer has proper structured sections.
    Expects markdown headers (##) or ALL CAPS section labels.
    """
    has_headers = bool(
        re.search(r'^##\s+\w+', answer, re.MULTILINE) or
        re.search(r'^[A-Z]{3,}', answer, re.MULTILINE)
    )
    has_content = len(answer.split()) >= 30
    passed      = has_headers and has_content

    return {
        "score":  1.0 if passed else 0.5,
        "passed": passed,
        "detail": (
            "Answer has structured sections and content."
            if passed else
            "Answer lacks structure or is too short."
        )
    }


# ─────────────────────────────────────────────
# COMPOSITE CASE SCORER
# ─────────────────────────────────────────────

# Component weights — must sum to 1.0
WEIGHTS = {
    "intent":           0.20,
    "keyword_coverage": 0.20,
    "disclaimer":       0.15,
    "confidence":       0.10,
    "risk_range":       0.10,
    "guardrail_block":  0.15,
    "urgency":          0.05,
    "answer_structure": 0.05
}


def score_test_case(
    test_case: Dict,
    response:  Dict
) -> Dict:
    """
    Score a single test case against its expected outcomes.
    Returns detailed per-component scores and overall score.
    """
    answer     = response.get("answer", "")
    guardrails = response.get("guardrails", {})
    guidance   = response.get("guidance", {})

    # Extract actual values safely
    actual_intent    = response.get("intent")
    actual_conf      = response.get("confidence", 0.0)
    actual_risk      = response.get("risk_score", 0.0) or 0.0
    actual_urgency   = guidance.get("urgency") if guidance else None

    # Run all component scorers
    components = {
        "intent": score_intent(
            test_case.get("expected_intent"),
            actual_intent
        ),
        "keyword_coverage": score_keyword_coverage(
            answer,
            test_case.get("expected_keywords", []),
            test_case.get("forbidden_keywords", [])
        ),
        "disclaimer": score_disclaimer(
            answer,
            test_case.get("must_contain_disclaimer", False)
        ),
        "confidence": score_confidence(
            actual_conf,
            test_case.get("min_confidence", 0.0)
        ),
        "risk_range": score_risk_range(
            actual_risk,
            test_case.get("min_risk_score", 0),
            test_case.get("max_risk_score", 100)
        ),
        "guardrail_block": score_guardrail_block(
            guardrails,
            test_case.get("should_be_blocked", False)
        ),
        "urgency": score_urgency(
            actual_urgency,
            test_case.get("expected_urgency", [])
        ),
        "answer_structure": score_answer_structure(answer)
    }

    # Weighted overall score
    overall = sum(
        components[k]["score"] * WEIGHTS[k]
        for k in WEIGHTS
    )

    passed_count = sum(1 for v in components.values() if v["passed"])
    total_checks = len(components)

    return {
        "test_id":       test_case["id"],
        "category":      test_case["category"],
        "query":         test_case["query"],
        "overall_score": round(overall, 3),
        "passed":        overall >= 0.6,
        "pass_rate":     f"{passed_count}/{total_checks}",
        "components":    components,
        "actual": {
            "intent":    actual_intent,
            "confidence": actual_conf,
            "risk_score": actual_risk,
            "urgency":    actual_urgency
        }
    }