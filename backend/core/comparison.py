"""Phase 7 comparison logic."""
import re
import json
import time
from typing import Dict, List, Optional, Tuple
from utils.logger import logger
from core.llm_provider import call_llm, safe_parse_json
from core.contract import (
    extract_clauses_static,
    analyse_contract,
    CLAUSE_TYPES,
    _score_to_label
)


# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────

'''def get_client() -> genai.GenerativeModel:
    key = settings.GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing.")
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash") '''


# ─────────────────────────────────────────────
# STATIC CLAUSE DIFFER
# ─────────────────────────────────────────────

def _diff_clauses_static(
    clauses_a: Dict[str, List[str]],
    clauses_b: Dict[str, List[str]]
) -> List[Dict]:
    """
    Compare static clause extractions from both documents.
    Returns list of per-clause-type diff dicts.
    No LLM — pure rule-based comparison.
    """
    diffs = []

    all_types = set(list(clauses_a.keys()) + list(clauses_b.keys()))

    for clause_type in sorted(all_types):
        sents_a = clauses_a.get(clause_type, [])
        sents_b = clauses_b.get(clause_type, [])

        present_a = len(sents_a) > 0
        present_b = len(sents_b) > 0

        # Determine difference type
        if present_a and present_b:
            diff_type = "modified"
        elif present_a and not present_b:
            diff_type = "removed"
        elif not present_a and present_b:
            diff_type = "added"
        else:
            continue  # neither has it — skip

        # Simple word-overlap similarity score
        words_a = set(" ".join(sents_a).lower().split())
        words_b = set(" ".join(sents_b).lower().split())
        union   = words_a | words_b
        overlap = words_a & words_b
        similarity = round(len(overlap) / len(union), 2) if union else 1.0

        diffs.append({
            "clause_type":  clause_type,
            "diff_type":    diff_type,
            "present_in_a": present_a,
            "present_in_b": present_b,
            "similarity":   similarity,
            "text_a":       " ".join(sents_a)[:300] if sents_a else "",
            "text_b":       " ".join(sents_b)[:300] if sents_b else "",
            "change_summary": _describe_diff(clause_type, diff_type, similarity)
        })

    return diffs


def _describe_diff(
    clause_type: str,
    diff_type: str,
    similarity: float
) -> str:
    """Generate a plain-English description of the change."""
    name = clause_type.replace("_", " ").title()

    if diff_type == "added":
        return f"{name} clause present in Document B but missing in Document A."
    if diff_type == "removed":
        return f"{name} clause present in Document A but missing in Document B."
    if similarity >= 0.85:
        return f"{name} clause is nearly identical in both documents."
    if similarity >= 0.5:
        return f"{name} clause has moderate changes between documents."
    return f"{name} clause has significant differences between documents."


# ─────────────────────────────────────────────
# COMPARISON PROMPT BUILDER
# ─────────────────────────────────────────────

def _build_comparison_prompt(
    text_a:     str,
    text_b:     str,
    name_a:     str,
    name_b:     str,
    static_diff: List[Dict]
) -> str:
    """
    Build unified comparison prompt.
    Includes static diff as hints to guide the LLM.
    Truncates both documents to manage token usage.
    """
    words_a   = text_a.split()
    words_b   = text_b.split()
    trunc_a   = " ".join(words_a[:2000])
    trunc_b   = " ".join(words_b[:2000])
    cut_a     = "[truncated]" if len(words_a) > 2000 else ""
    cut_b     = "[truncated]" if len(words_b) > 2000 else ""

    # Format static diff as hints
    diff_hints = []
    for d in static_diff[:8]:
        diff_hints.append(
            f"- {d['clause_type'].upper()} ({d['diff_type']}): "
            f"{d['change_summary']}"
        )
    hints_block = (
        "\n".join(diff_hints)
        if diff_hints
        else "No pre-identified differences."
    )

    return f"""You are an expert contract lawyer comparing two legal documents.

DOCUMENT A — {name_a} {cut_a}:
{trunc_a}

DOCUMENT B — {name_b} {cut_b}:
{trunc_b}

PRE-IDENTIFIED DIFFERENCES (use as starting points):
{hints_block}

YOUR TASK:
Compare these two documents clause by clause. For every significant
clause type found in either document, produce a comparison row.

RISK SCORING (per document):
- 0–34  → safe   ✅
- 35–69 → risky  ⚠️
- 70–100→ unfair 🚨

Respond ONLY with this exact JSON — no markdown, no extra text:
{{
  "comparison_rows": [
    {{
      "clause_type":    "<clause type>",
      "clause_title":   "<short human-readable title>",
      "text_a":         "<clause text from doc A, max 200 chars, or 'Not present'>",
      "text_b":         "<clause text from doc B, max 200 chars, or 'Not present'>",
      "risk_label_a":   "safe|risky|unfair",
      "risk_score_a":   <0-100>,
      "risk_label_b":   "safe|risky|unfair",
      "risk_score_b":   <0-100>,
      "difference":     "<one sentence describing the key difference>",
      "favours":        "doc_a|doc_b|neither|both",
      "severity":       "low|medium|high"
    }}
  ],
  "overall_risk_score_a":  <0-100>,
  "overall_risk_score_b":  <0-100>,
  "overall_risk_label_a":  "safe|risky|unfair",
  "overall_risk_label_b":  "safe|risky|unfair",
  "riskier_document":      "doc_a|doc_b|equal",
  "key_differences": [
    "<most important difference 1>",
    "<difference 2>",
    "<difference 3>"
  ],
  "advantages_a": ["<advantage of doc A over B>", "<advantage 2>"],
  "advantages_b": ["<advantage of doc B over A>", "<advantage 2>"],
  "recommendation": "prefer_a|prefer_b|negotiate_both|reject_both",
  "recommendation_reason": "<two sentence plain-English explanation>"
}}
"""


# ─────────────────────────────────────────────
# FALLBACK BUILDER
# ─────────────────────────────────────────────

def _build_comparison_fallback(
    static_diff: List[Dict],
    analysis_a:  Dict,
    analysis_b:  Dict,
    name_a:      str,
    name_b:      str
) -> Dict:
    """
    Build a static comparison result when LLM is unavailable.
    Uses pre-computed clause analyses and static diff.
    """
    rows = []
    for d in static_diff:
        risk_a = analysis_a.get("overall_risk_score", 50)
        risk_b = analysis_b.get("overall_risk_score", 50)
        rows.append({
            "clause_type":  d["clause_type"],
            "clause_title": d["clause_type"].replace("_", " ").title(),
            "text_a":       d["text_a"][:200] or "Not present",
            "text_b":       d["text_b"][:200] or "Not present",
            "risk_label_a": _score_to_label(risk_a),
            "risk_score_a": risk_a,
            "risk_label_b": _score_to_label(risk_b),
            "risk_score_b": risk_b,
            "difference":   d["change_summary"],
            "favours":      "neither",
            "severity":     "medium"
        })

    score_a = analysis_a.get("overall_risk_score", 50)
    score_b = analysis_b.get("overall_risk_score", 50)

    riskier = (
        "doc_a" if score_a > score_b else
        "doc_b" if score_b > score_a else
        "equal"
    )
    recommendation = (
        "prefer_b" if score_a > score_b else
        "prefer_a" if score_b > score_a else
        "negotiate_both"
    )

    return {
        "comparison_rows":       rows,
        "overall_risk_score_a":  score_a,
        "overall_risk_score_b":  score_b,
        "overall_risk_label_a":  _score_to_label(score_a),
        "overall_risk_label_b":  _score_to_label(score_b),
        "riskier_document":      riskier,
        "key_differences": [
            d["change_summary"] for d in static_diff[:3]
        ],
        "advantages_a":          [],
        "advantages_b":          [],
        "recommendation":        recommendation,
        "recommendation_reason": (
            f"Based on static analysis: {name_a} scores {score_a}/100, "
            f"{name_b} scores {score_b}/100. "
            "LLM analysis unavailable — review manually."
        )
    }


# ─────────────────────────────────────────────
# RESULT VALIDATOR
# ─────────────────────────────────────────────

def _validate_comparison_result(result: Dict) -> Dict:
    """Fill all missing keys with safe defaults."""

    result.setdefault("comparison_rows",      [])
    result.setdefault("overall_risk_score_a", 50)
    result.setdefault("overall_risk_score_b", 50)
    result.setdefault("overall_risk_label_a", "risky")
    result.setdefault("overall_risk_label_b", "risky")
    result.setdefault("riskier_document",     "equal")
    result.setdefault("key_differences",      [])
    result.setdefault("advantages_a",         [])
    result.setdefault("advantages_b",         [])
    result.setdefault("recommendation",       "negotiate_both")
    result.setdefault("recommendation_reason","Review both documents carefully.")

    # Validate each row
    valid_rows = []
    for row in result["comparison_rows"]:
        if not isinstance(row, dict):
            continue
        row.setdefault("clause_type",  "other")
        row.setdefault("clause_title", "Unnamed Clause")
        row.setdefault("text_a",       "Not present")
        row.setdefault("text_b",       "Not present")
        row.setdefault("risk_label_a", "risky")
        row.setdefault("risk_score_a", 50)
        row.setdefault("risk_label_b", "risky")
        row.setdefault("risk_score_b", 50)
        row.setdefault("difference",   "")
        row.setdefault("favours",      "neither")
        row.setdefault("severity",     "medium")

        # Clamp scores
        row["risk_score_a"] = max(0, min(100, int(row["risk_score_a"])))
        row["risk_score_b"] = max(0, min(100, int(row["risk_score_b"])))

        # Validate labels
        for key in ("risk_label_a", "risk_label_b"):
            score_key = key.replace("label", "score")
            if row[key] not in ("safe", "risky", "unfair"):
                row[key] = _score_to_label(row[score_key])

        # Validate favours
        if row["favours"] not in ("doc_a", "doc_b", "neither", "both"):
            row["favours"] = "neither"

        # Validate severity
        if row["severity"] not in ("low", "medium", "high"):
            row["severity"] = "medium"

        valid_rows.append(row)

    result["comparison_rows"] = valid_rows

    # Validate overall labels
    for key in ("overall_risk_label_a", "overall_risk_label_b"):
        score_key = key.replace("label", "score")
        if result[key] not in ("safe", "risky", "unfair"):
            result[key] = _score_to_label(result[score_key])

    # Validate riskier
    if result["riskier_document"] not in ("doc_a", "doc_b", "equal"):
        result["riskier_document"] = "equal"

    # Validate recommendation
    valid_recs = ("prefer_a", "prefer_b", "negotiate_both", "reject_both")
    if result["recommendation"] not in valid_recs:
        result["recommendation"] = "negotiate_both"

    return result


# ─────────────────────────────────────────────
# FORMAT FOR API RESPONSE
# ─────────────────────────────────────────────

RISK_DISPLAY = {
    "safe":   "✅ SAFE",
    "risky":  "⚠️ RISKY",
    "unfair": "🚨 UNFAIR"
}

RECOMMENDATION_DISPLAY = {
    "prefer_a":       "✅ PREFER DOCUMENT A",
    "prefer_b":       "✅ PREFER DOCUMENT B",
    "negotiate_both": "⚠️ NEGOTIATE BOTH",
    "reject_both":    "🚨 REJECT BOTH"
}

SEVERITY_DISPLAY = {
    "low":    "🟢 LOW",
    "medium": "🟡 MEDIUM",
    "high":   "🔴 HIGH"
}

FAVOURS_DISPLAY = {
    "doc_a":   "Favours Document A",
    "doc_b":   "Favours Document B",
    "neither": "Neutral",
    "both":    "Favours Both"
}


def format_comparison_for_response(
    result:  Dict,
    name_a:  str,
    name_b:  str
) -> Dict:
    """
    Format raw comparison dict into clean numbered API-ready structure.
    """
    # Format rows
    formatted_rows = []
    for i, row in enumerate(result["comparison_rows"], 1):
        formatted_rows.append({
            "row_number":     i,
            "clause_type":    row["clause_type"],
            "clause_title":   row["clause_title"],
            "text_a":         row["text_a"],
            "text_b":         row["text_b"],
            "risk_label_a":   row["risk_label_a"],
            "risk_display_a": RISK_DISPLAY.get(row["risk_label_a"], "⚠️ RISKY"),
            "risk_score_a":   row["risk_score_a"],
            "risk_label_b":   row["risk_label_b"],
            "risk_display_b": RISK_DISPLAY.get(row["risk_label_b"], "⚠️ RISKY"),
            "risk_score_b":   row["risk_score_b"],
            "difference":     row["difference"],
            "favours":        row["favours"],
            "favours_display":FAVOURS_DISPLAY.get(row["favours"], "Neutral"),
            "severity":       row["severity"],
            "severity_display": SEVERITY_DISPLAY.get(row["severity"], "🟡 MEDIUM")
        })

    # High severity rows for quick highlight
    high_severity = [
        r for r in formatted_rows if r["severity"] == "high"
    ]

    rec = result.get("recommendation", "negotiate_both")

    return {
        "document_a_name":        name_a,
        "document_b_name":        name_b,
        "comparison_table":       formatted_rows,
        "total_clauses_compared": len(formatted_rows),
        "high_severity_count":    len(high_severity),
        "high_severity_clauses":  high_severity,
        "overall_risk_score_a":   result["overall_risk_score_a"],
        "overall_risk_score_b":   result["overall_risk_score_b"],
        "overall_risk_display_a": RISK_DISPLAY.get(
            result["overall_risk_label_a"], "⚠️ RISKY"
        ),
        "overall_risk_display_b": RISK_DISPLAY.get(
            result["overall_risk_label_b"], "⚠️ RISKY"
        ),
        "riskier_document":       result["riskier_document"],
        "riskier_display": (
            f"{name_a} is riskier"   if result["riskier_document"] == "doc_a" else
            f"{name_b} is riskier"   if result["riskier_document"] == "doc_b" else
            "Both carry equal risk"
        ),
        "key_differences":        result["key_differences"],
        "advantages_a":           result["advantages_a"],
        "advantages_b":           result["advantages_b"],
        "recommendation":         rec,
        "recommendation_display": RECOMMENDATION_DISPLAY.get(
            rec, "⚠️ NEGOTIATE BOTH"
        ),
        "recommendation_reason":  result["recommendation_reason"]
    }


# ─────────────────────────────────────────────
# LLM COMPARISON
# ─────────────────────────────────────────────

def compare_contracts_llm(
    text_a:      str,
    text_b:      str,
    name_a:      str,
    name_b:      str,
    static_diff: List[Dict],
    analysis_a:  Dict,
    analysis_b:  Dict,
    retries:     int = 3
) -> Dict:
    """
    Single Ollama call to compare both contracts.
    """
    prompt   = _build_comparison_prompt(
        text_a, text_b, name_a, name_b, static_diff
    )
    fallback = _build_comparison_fallback(
        static_diff, analysis_a, analysis_b, name_a, name_b
    )

    for attempt in range(retries):
        try:
            raw    = call_llm(prompt, max_tokens=2048, expect_json=True)
            result = safe_parse_json(raw, fallback)
            result = _validate_comparison_result(result)

            logger.info(
                f"[Comparison] Done — "
                f"{len(result['comparison_rows'])} rows | "
                f"rec: {result['recommendation']}"
            )
            return result

        except RuntimeError as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"[Comparison] LLM error — retrying in {wait}s: {e}"
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"[Comparison] LLM failed: {e} — static fallback."
                )
                return fallback

    return fallback


# ─────────────────────────────────────────────
# MASTER COMPARE FUNCTION
# ─────────────────────────────────────────────

def compare_contracts(
    text_a:   str,
    text_b:   str,
    name_a:   str = "Document A",
    name_b:   str = "Document B",
    use_llm:  bool = True
) -> Dict:
    """
    Master comparison function.

    Pipeline:
    1. Static clause extraction on both docs   (no LLM)
    2. Static clause diff                       (no LLM)
    3. Individual contract risk analysis        (no LLM — static mode)
    4. LLM deep comparison                     (1 LLM call) OR static fallback
    5. Format and return

    Total LLM calls: 1 (or 0 if use_llm=False)
    """
    logger.info(
        f"[Comparison] Comparing '{name_a}' vs '{name_b}' | "
        f"LLM: {use_llm}"
    )

    # Step 1: static extraction
    clauses_a = extract_clauses_static(text_a)
    clauses_b = extract_clauses_static(text_b)

    logger.info(
        f"[Comparison] Static extraction — "
        f"A: {sum(len(v) for v in clauses_a.values())} sentences | "
        f"B: {sum(len(v) for v in clauses_b.values())} sentences"
    )

    # Step 2: static diff
    static_diff = _diff_clauses_static(clauses_a, clauses_b)
    logger.info(
        f"[Comparison] Static diff — {len(static_diff)} clause types compared"
    )

    # Step 3: individual risk analysis (static only — no extra LLM call)
    analysis_a = analyse_contract(text_a, name_a, use_llm=False)
    analysis_b = analyse_contract(text_b, name_b, use_llm=False)

    # Step 4: LLM or static fallback
    if use_llm:
        result = compare_contracts_llm(
            text_a, text_b, name_a, name_b,
            static_diff, analysis_a, analysis_b
        )
    else:
        logger.info("[Comparison] LLM disabled — using static fallback.")
        result = _build_comparison_fallback(
            static_diff, analysis_a, analysis_b, name_a, name_b
        )
        result = _validate_comparison_result(result)

    # Step 5: format
    return format_comparison_for_response(result, name_a, name_b)