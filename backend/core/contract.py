"""Phase 6 contract logic."""
import re
import json
import time
#import google.generativeai as genai
from typing import Dict, List, Optional
from core.llm_provider import call_llm
from config import settings
from utils.logger import logger
from core.agents import safe_parse_json
from core.llm_provider import call_llm, safe_parse_json as _sp

# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────

#def get_client() -> genai.GenerativeModel:
 #   key = settings.GEMINI_API_KEY
  #  if not key:
  #      raise RuntimeError("GEMINI_API_KEY missing.")
  #  genai.configure(api_key=key)
   # return genai.GenerativeModel("gemini-2.5-flash")


# ─────────────────────────────────────────────
# CLAUSE TYPE DEFINITIONS
# ─────────────────────────────────────────────

CLAUSE_TYPES = {
    "deposit": {
        "keywords": [
            "deposit", "security deposit", "advance", "retainer",
            "upfront payment", "earnest money"
        ],
        "description": "Payment held as security or advance"
    },
    "penalty": {
        "keywords": [
            "penalty", "liquidated damages", "fine", "late fee",
            "interest on delay", "breach fee", "forfeiture"
        ],
        "description": "Financial consequences for breach or delay"
    },
    "obligations": {
        "keywords": [
            "shall", "must", "obligated", "required to", "responsible for",
            "duty", "covenant", "undertakes", "agrees to", "liable to"
        ],
        "description": "Duties and responsibilities of each party"
    },
    "termination": {
        "keywords": [
            "termination", "terminate", "cancel", "cancellation",
            "expiry", "expiration", "end of agreement", "notice period",
            "without cause", "for cause"
        ],
        "description": "Conditions and procedures for ending the contract"
    },
    "indemnity": {
        "keywords": [
            "indemnify", "indemnification", "hold harmless",
            "defend", "indemnitor", "indemnitee"
        ],
        "description": "Who bears liability for losses or damages"
    },
    "dispute_resolution": {
        "keywords": [
            "arbitration", "mediation", "jurisdiction", "governing law",
            "dispute", "litigation", "court", "tribunal"
        ],
        "description": "How disagreements between parties are resolved"
    },
    "confidentiality": {
        "keywords": [
            "confidential", "non-disclosure", "NDA", "proprietary",
            "trade secret", "not disclose", "keep confidential"
        ],
        "description": "Obligations to protect sensitive information"
    },
    "limitation_of_liability": {
        "keywords": [
            "limitation of liability", "limit of liability", "cap on liability",
            "maximum liability", "not liable for", "exclude liability"
        ],
        "description": "Caps or exclusions on what a party can be held liable for"
    }
}

# Risk label definitions
RISK_LABELS = {
    "safe":   {"emoji": "✅", "display": "✅ SAFE",   "score_range": (0,  34)},
    "risky":  {"emoji": "⚠️", "display": "⚠️ RISKY",  "score_range": (35, 69)},
    "unfair": {"emoji": "🚨", "display": "🚨 UNFAIR", "score_range": (70, 100)}
}


# ─────────────────────────────────────────────
# STATIC CLAUSE EXTRACTOR (no LLM)
# ─────────────────────────────────────────────

def extract_clauses_static(text: str) -> Dict[str, List[str]]:
    """
    Rule-based clause extractor.
    Splits contract into sentences and matches keyword patterns.
    Returns dict of clause_type → list of matched sentences.
    Used as fallback and to pre-populate context for LLM.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    found: Dict[str, List[str]] = {k: [] for k in CLAUSE_TYPES}

    for sentence in sentences:
        sentence_lower = sentence.lower()
        for clause_type, config in CLAUSE_TYPES.items():
            for keyword in config["keywords"]:
                if keyword.lower() in sentence_lower:
                    # Avoid duplicates
                    if sentence not in found[clause_type]:
                        found[clause_type].append(sentence)
                    break  # one match per sentence per clause type

    # Keep max 5 sentences per clause type to limit token usage
    for k in found:
        found[k] = found[k][:5]

    total = sum(len(v) for v in found.values())
    logger.info(f"[Contract] Static extractor found {total} clause sentences.")
    return found


# ─────────────────────────────────────────────
# CONTRACT ANALYSIS PROMPT
# ─────────────────────────────────────────────

def _build_contract_prompt(
    contract_text: str,
    static_clauses: Dict[str, List[str]],
    filename: str = "contract"
) -> str:
    """
    Build the unified contract analysis prompt.
    Includes pre-extracted clause hints from static extractor.
    """
    # Build clause hints block
    hints = []
    for clause_type, sentences in static_clauses.items():
        if sentences:
            hints.append(
                f"{clause_type.upper()}:\n" +
                "\n".join(f"  - {s[:200]}" for s in sentences[:3])
            )
    hints_block = "\n\n".join(hints) if hints else "No clauses pre-identified."

    # Truncate contract text to avoid token overflow
    # Keep first 3000 words — covers most contracts
    words      = contract_text.split()
    truncated  = " ".join(words[:3000])
    was_cut    = len(words) > 3000
    cut_notice = "\n[Note: Contract truncated to first 3000 words for analysis]" if was_cut else ""

    return f"""You are an expert contract lawyer performing a detailed contract analysis.

DOCUMENT: {filename}{cut_notice}

PRE-IDENTIFIED CLAUSE HINTS (use these as starting points):
{hints_block}

FULL CONTRACT TEXT:
{truncated}

YOUR TASK:
Analyse this contract and extract ALL significant clauses.
For each clause found, assess its risk to the signing party.

RISK LABEL RULES:
- "safe"   → standard, balanced, industry-normal terms (score 0–34)
- "risky"  → unusual, one-sided, or potentially harmful terms (score 35–69)
- "unfair" → exploitative, illegal, or severely one-sided terms (score 70–100)

Respond ONLY with this exact JSON — no markdown, no extra text:
{{
  "clauses": [
    {{
      "type": "<deposit|penalty|obligations|termination|indemnity|dispute_resolution|confidentiality|limitation_of_liability|other>",
      "title": "<short clause title>",
      "text": "<exact or paraphrased clause text, max 300 chars>",
      "risk_label": "safe|risky|unfair",
      "risk_score": <0-100>,
      "reason": "<one sentence explaining the risk assessment>",
      "page_hint": "<approximate location: 'early', 'middle', 'late', or page number if visible>"
    }}
  ],
  "overall_risk_score": <0-100>,
  "overall_risk_label": "safe|risky|unfair",
  "summary": "<2-3 sentence plain English summary of the contract's risk profile>",
  "critical_issues": ["<most concerning clause or issue 1>", "<issue 2>", "<issue 3>"],
  "positive_aspects": ["<fair or protective clause 1>", "<aspect 2>"],
  "recommendation": "sign|negotiate|reject",
  "recommendation_reason": "<one sentence explaining the recommendation>"
}}
"""


# ─────────────────────────────────────────────
# LLM CONTRACT ANALYSER
# ─────────────────────────────────────────────

def analyse_contract_llm(
    contract_text: str,
    static_clauses: Dict[str, List[str]],
    filename: str = "contract",
    retries: int = 4
) -> Dict:
    """
    Send contract to Gemini for deep clause analysis.
    Returns structured analysis dict.
    """
    #model  = get_client()
    prompt = _build_contract_prompt(contract_text, static_clauses, filename)

    fallback = _build_contract_fallback(static_clauses)

    for attempt in range(retries):
        try:

            raw = call_llm(
                prompt     = prompt,
                max_tokens = 2048,
                expect_json= True
            )
            #raw    = response.text.strip()
            #raw    = re.sub(r"^```(?:json)?\s*", "", raw).strip()
            #raw    = re.sub(r"\s*```$",           "", raw).strip()
            result = safe_parse_json(raw, fallback)
            result = _validate_contract_result(result, static_clauses)

            logger.info(
                f"[Contract] Analysis complete — "
                f"{len(result['clauses'])} clauses | "
                f"risk: {result['overall_risk_label']} "
                f"({result['overall_risk_score']})"
            )
            return result

        except RuntimeError as e:
            # Ollama offline or timeout
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"[Contract] LLM error — retrying in {wait}s: {e}"
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"[Contract] LLM failed: {e} — using static fallback."
                )
                return fallback

    return fallback


# ─────────────────────────────────────────────
# STATIC FALLBACK ANALYSIS
# ─────────────────────────────────────────────

def _build_contract_fallback(
    static_clauses: Dict[str, List[str]]
) -> Dict:
    """
    Build a rule-based fallback analysis when LLM is unavailable.
    Uses static clause extraction + heuristic risk scoring.
    """
    clauses = []

    for clause_type, sentences in static_clauses.items():
        for sentence in sentences:
            # Heuristic risk scoring
            risk_score, risk_label, reason = _heuristic_risk(
                clause_type, sentence
            )
            clauses.append({
                "type":       clause_type,
                "title":      clause_type.replace("_", " ").title(),
                "text":       sentence[:300],
                "risk_label": risk_label,
                "risk_score": risk_score,
                "reason":     reason,
                "page_hint":  "unknown"
            })

    # Overall score = average of clause scores (or 50 if none found)
    scores = [c["risk_score"] for c in clauses]
    overall_score = int(sum(scores) / len(scores)) if scores else 50
    overall_label = _score_to_label(overall_score)

    return {
        "clauses":             clauses,
        "overall_risk_score":  overall_score,
        "overall_risk_label":  overall_label,
        "summary":             (
            f"Static analysis identified {len(clauses)} clauses. "
            "LLM analysis unavailable — results are approximate. "
            "Please review manually or retry later."
        ),
        "critical_issues":     [
            c["text"][:100]
            for c in clauses
            if c["risk_label"] == "unfair"
        ][:3],
        "positive_aspects":    [
            c["text"][:100]
            for c in clauses
            if c["risk_label"] == "safe"
        ][:2],
        "recommendation":        "negotiate",
        "recommendation_reason": (
            "Full LLM analysis unavailable. Manual review recommended."
        )
    }


def _heuristic_risk(
    clause_type: str,
    text: str
) -> tuple:
    """
    Simple heuristic to assign risk scores without LLM.
    Returns (score, label, reason).
    """
    text_lower = text.lower()

    # High-risk patterns
    high_risk_patterns = [
        "without cause", "sole discretion", "non-refundable",
        "unlimited liability", "waive all rights", "irrevocable",
        "penalty of", "forfeit", "absolute", "no recourse",
        "unilateral", "at our discretion"
    ]

    # Medium-risk patterns
    medium_risk_patterns = [
        "liquidated damages", "late fee", "interest", "penalty",
        "terminate immediately", "without notice", "indemnify",
        "hold harmless", "not liable"
    ]

    score = 20  # start safe

    for p in high_risk_patterns:
        if p in text_lower:
            score += 30
            break

    for p in medium_risk_patterns:
        if p in text_lower:
            score += 20
            break

    # Clause type inherent risk
    type_base = {
        "penalty":               15,
        "indemnity":             15,
        "limitation_of_liability": 10,
        "termination":           10,
        "deposit":                5,
        "obligations":            5,
        "dispute_resolution":     5,
        "confidentiality":        5
    }
    score += type_base.get(clause_type, 0)
    score  = min(score, 100)

    label  = _score_to_label(score)
    reason = (
        f"Heuristic analysis of {clause_type.replace('_', ' ')} clause. "
        "Review manually for accuracy."
    )
    return score, label, reason


def _score_to_label(score: int) -> str:
    if score >= 70:
        return "unfair"
    if score >= 35:
        return "risky"
    return "safe"


# ─────────────────────────────────────────────
# RESULT VALIDATOR
# ─────────────────────────────────────────────

def _validate_contract_result(
    result: Dict,
    static_clauses: Dict[str, List[str]]
) -> Dict:
    """
    Ensure all required keys exist and values are valid.
    """
    result.setdefault("clauses",             [])
    result.setdefault("overall_risk_score",  50)
    result.setdefault("overall_risk_label",  "risky")
    result.setdefault("summary",             "Analysis complete.")
    result.setdefault("critical_issues",     [])
    result.setdefault("positive_aspects",    [])
    result.setdefault("recommendation",      "negotiate")
    result.setdefault("recommendation_reason", "Review all clauses carefully.")

    # Validate each clause
    valid_clauses = []
    for clause in result["clauses"]:
        if not isinstance(clause, dict):
            continue
        clause.setdefault("type",       "other")
        clause.setdefault("title",      "Unnamed Clause")
        clause.setdefault("text",       "")
        clause.setdefault("risk_label", "risky")
        clause.setdefault("risk_score", 50)
        clause.setdefault("reason",     "")
        clause.setdefault("page_hint",  "unknown")

        # Clamp score
        clause["risk_score"] = max(0, min(100, int(clause["risk_score"])))

        # Validate label
        if clause["risk_label"] not in ("safe", "risky", "unfair"):
            clause["risk_label"] = _score_to_label(clause["risk_score"])

        valid_clauses.append(clause)

    result["clauses"] = valid_clauses

    # If LLM returned no clauses, fall back to static
    if not result["clauses"]:
        fallback = _build_contract_fallback(static_clauses)
        result["clauses"] = fallback["clauses"]

    # Validate overall label
    if result["overall_risk_label"] not in ("safe", "risky", "unfair"):
        result["overall_risk_label"] = _score_to_label(
            result["overall_risk_score"]
        )

    # Validate recommendation
    if result["recommendation"] not in ("sign", "negotiate", "reject"):
        result["recommendation"] = "negotiate"

    return result


# ─────────────────────────────────────────────
# FORMAT FOR API RESPONSE
# ─────────────────────────────────────────────

def format_contract_analysis(analysis: Dict) -> Dict:
    """
    Format raw analysis dict into clean API-ready structure
    with display labels and emoji.
    """
    def label_display(label: str) -> str:
        return RISK_LABELS.get(label, RISK_LABELS["risky"])["display"]

    recommendation_display = {
        "sign":      "✅ SAFE TO SIGN",
        "negotiate": "⚠️ NEGOTIATE BEFORE SIGNING",
        "reject":    "🚨 DO NOT SIGN"
    }.get(analysis.get("recommendation", "negotiate"), "⚠️ NEGOTIATE BEFORE SIGNING")

    formatted_clauses = []
    for clause in analysis.get("clauses", []):
        formatted_clauses.append({
            "type":            clause["type"],
            "title":           clause["title"],
            "text":            clause["text"],
            "risk_label":      clause["risk_label"],
            "risk_display":    label_display(clause["risk_label"]),
            "risk_score":      clause["risk_score"],
            "reason":          clause["reason"],
            "page_hint":       clause.get("page_hint", "unknown")
        })

    # Group clauses by risk label for easy frontend rendering
    grouped = {"unfair": [], "risky": [], "safe": []}
    for c in formatted_clauses:
        grouped[c["risk_label"]].append(c)

    return {
        "clauses":                formatted_clauses,
        "clauses_grouped":        grouped,
        "clause_count":           len(formatted_clauses),
        "unfair_count":           len(grouped["unfair"]),
        "risky_count":            len(grouped["risky"]),
        "safe_count":             len(grouped["safe"]),
        "overall_risk_score":     analysis["overall_risk_score"],
        "overall_risk_label":     analysis["overall_risk_label"],
        "overall_risk_display":   label_display(analysis["overall_risk_label"]),
        "summary":                analysis["summary"],
        "critical_issues":        analysis.get("critical_issues", []),
        "positive_aspects":       analysis.get("positive_aspects", []),
        "recommendation":         analysis.get("recommendation", "negotiate"),
        "recommendation_display": recommendation_display,
        "recommendation_reason":  analysis.get("recommendation_reason", "")
    }


# ─────────────────────────────────────────────
# MASTER CONTRACT ANALYSER
# ─────────────────────────────────────────────

def analyse_contract(
    contract_text: str,
    filename: str = "contract",
    use_llm: bool = True
) -> Dict:
    """
    Master function:
    1. Static clause extraction (no LLM)
    2. LLM deep analysis (1 LLM call) OR static fallback
    3. Format and return
    """
    logger.info(
        f"[Contract] Analysing '{filename}' — "
        f"{len(contract_text.split())} words"
    )

    # Step 1: static extraction (always runs, no LLM)
    static_clauses = extract_clauses_static(contract_text)

    # Step 2: LLM or static-only
    if use_llm:
        analysis = analyse_contract_llm(
            contract_text, static_clauses, filename
        )
    else:
        logger.info("[Contract] LLM disabled — using static analysis only.")
        analysis = _build_contract_fallback(static_clauses)

    # Step 3: format
    return format_contract_analysis(analysis)