"""Helpers for detecting hallucinations in model outputs."""
import re
from typing import Dict, List
from utils.logger import logger


# ─────────────────────────────────────────────
# DETECTION PATTERNS
# ─────────────────────────────────────────────

FABRICATED_CITATION_PATTERNS = [
    r'\b[A-Z][a-z]+ v\.? [A-Z][a-z]+,?\s*\d{3,4}\b',
    r'\bSection\s+\d+[A-Z]?\s+of\s+the\s+[A-Z][a-zA-Z\s]+Act\b',
    r'\b[A-Z][a-zA-Z\s]+Act,?\s*(19|20)\d{2}\b',
    r'\b\d+\s+U\.S\.C\.?\s+§?\s*\d+\b',
    r'\b\d+\s+C\.F\.R\.?\s+§?\s*\d+\b',
    r'\b\d+\s+[A-Z][a-z]*\.?\s*\d[a-z]*\s+\d+\b',
]

OVERCONFIDENT_PHRASES = [
    "as established in the landmark case",
    "the law clearly states",
    "it is well established",
    "the statute explicitly states",
    "case law confirms",
    "judicial precedent establishes",
    "the court held in",
    "per the ruling in",
    "you are legally entitled to exactly",
    "the exact penalty is",
    "without any doubt",
    "100% certain",
    "guaranteed to win",
    "you cannot lose",
    "definitely illegal",
    "definitely legal",
]

ABSOLUTE_PATTERNS = [
    r'\byou (will|shall) definitely\b',
    r'\b100%\s*(certain|guaranteed|sure|legal|illegal)\b',
    r'\bno (court|judge|lawyer) (will|would|can)\b',
    r'\byou (cannot|can never) lose\b',
    r'\bguaranteed (to|that)\b',
]

CONTEXT_FABRICATION_SIGNALS = [
    "according to my knowledge",
    "based on my training",
    "i know that",
    "it is a fact that",
    "research shows that",
    "studies confirm",
    "experts agree",
]


# ─────────────────────────────────────────────
# DETECTORS
# ─────────────────────────────────────────────

def detect_fabricated_citations(text: str) -> List[Dict]:
    """Detect potentially fabricated legal citations."""
    findings = []
    for pattern in FABRICATED_CITATION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "type":    "fabricated_citation",
                "match":   match.group(),
                "position": match.start(),
                "severity": "high"
            })
    return findings


def detect_overconfident_phrases(text: str) -> List[Dict]:
    """Detect phrases indicating overconfident or fabricated claims."""
    text_lower = text.lower()
    findings   = []
    for phrase in OVERCONFIDENT_PHRASES:
        idx = text_lower.find(phrase)
        if idx >= 0:
            findings.append({
                "type":     "overconfident_phrase",
                "match":    phrase,
                "position": idx,
                "severity": "medium"
            })
    return findings


def detect_absolute_claims(text: str) -> List[Dict]:
    """Detect absolute guarantee-style claims."""
    findings = []
    for pattern in ABSOLUTE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "type":     "absolute_claim",
                "match":    match.group(),
                "position": match.start(),
                "severity": "medium"
            })
    return findings


def detect_context_fabrication(text: str) -> List[Dict]:
    """Detect signals the model is using training knowledge vs context."""
    text_lower = text.lower()
    findings   = []
    for phrase in CONTEXT_FABRICATION_SIGNALS:
        idx = text_lower.find(phrase)
        if idx >= 0:
            findings.append({
                "type":     "context_fabrication",
                "match":    phrase,
                "position": idx,
                "severity": "low"
            })
    return findings


def detect_uncertainty_absence(text: str, min_markers: int = 2) -> Dict:
    """
    Check if answer lacks uncertainty markers — a sign of overconfidence.
    """
    markers = [
        "typically", "generally", "usually", "often", "may", "might",
        "could", "consult", "verify", "jurisdiction", "varies",
        "depending", "in most cases", "as a general rule", "generally speaking"
    ]
    text_lower    = text.lower()
    found_markers = [m for m in markers if m in text_lower]
    missing       = len(found_markers) < min_markers

    return {
        "type":           "uncertainty_absence",
        "markers_found":  found_markers,
        "marker_count":   len(found_markers),
        "severity":       "low" if not missing else "medium",
        "flagged":        missing,
        "detail": (
            f"Only {len(found_markers)} uncertainty markers found "
            f"(minimum {min_markers} expected)."
            if missing else
            f"{len(found_markers)} uncertainty markers present — good."
        )
    }


# ─────────────────────────────────────────────
# MASTER HALLUCINATION SCORER
# ─────────────────────────────────────────────

SEVERITY_SCORES = {
    "high":   3,
    "medium": 2,
    "low":    1
}


def analyse_hallucination_risk(answer: str) -> Dict:
    """
    Run all hallucination detectors on an answer.
    Returns structured hallucination analysis.
    """
    all_findings = []
    all_findings.extend(detect_fabricated_citations(answer))
    all_findings.extend(detect_overconfident_phrases(answer))
    all_findings.extend(detect_absolute_claims(answer))
    all_findings.extend(detect_context_fabrication(answer))

    uncertainty = detect_uncertainty_absence(answer)
    if uncertainty["flagged"]:
        all_findings.append({
            "type":     "uncertainty_absence",
            "match":    "missing uncertainty markers",
            "severity": uncertainty["severity"]
        })

    # Severity weighted score
    severity_total = sum(
        SEVERITY_SCORES.get(f["severity"], 1)
        for f in all_findings
    )

    # Risk level
    if severity_total >= 6:
        risk_level = "high"
    elif severity_total >= 3:
        risk_level = "medium"
    elif severity_total >= 1:
        risk_level = "low"
    else:
        risk_level = "none"

    high_findings   = [f for f in all_findings if f["severity"] == "high"]
    medium_findings = [f for f in all_findings if f["severity"] == "medium"]
    low_findings    = [f for f in all_findings if f["severity"] == "low"]

    return {
        "hallucination_risk":  risk_level,
        "total_findings":      len(all_findings),
        "severity_score":      severity_total,
        "high_severity":       high_findings,
        "medium_severity":     medium_findings,
        "low_severity":        low_findings,
        "uncertainty_check":   uncertainty,
        "safe":                risk_level in ("none", "low"),
        "findings":            all_findings
    }