import re
import json
import time
import requests
from typing import Optional
from config import settings
from utils.logger import logger


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

OLLAMA_GENERATE_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"

# Injected at the start of every JSON-expecting prompt
JSON_ENFORCEMENT = (
    "YOU MUST RESPOND WITH ONLY A VALID JSON OBJECT.\n"
    "DO NOT include markdown, code fences, backticks, or explanations.\n"
    "DO NOT write anything before or after the JSON.\n"
    "START your response with { and END with }.\n\n"
)

# Valid intent labels — single source of truth
VALID_INTENTS = {
    "tenant_rights",
    "contract_analysis",
    "contract_comparison",
    "consumer_rights",
    "employment_law",
    "criminal_law",
    "legal_notice",
    "document_generation",
    "general_legal"
}

DEFAULT_INTENT = "general_legal"


# ─────────────────────────────────────────────
# INTENT NORMALISER
# ─────────────────────────────────────────────

def normalise_intent(raw_intent) -> str:
    """
    Convert any intent representation into a single canonical string.

    Handles:
    - Correct string:  "employment_law"             → "employment_law"
    - Dict form:       {"employment_law": 0.92, ...} → "employment_law"
    - List form:       ["employment_law", ...]       → "employment_law"
    - Wrong case:      "Employment_Law"              → "employment_law"
    - Unknown value:   "something_else"              → "general_legal"
    - None / empty:    None                          → "general_legal"
    """
    if raw_intent is None:
        return DEFAULT_INTENT

    # Dict: {"employment_law": 0.92, "contract_analysis": 0.41}
    if isinstance(raw_intent, dict):
        if not raw_intent:
            return DEFAULT_INTENT
        # Pick key with highest value
        best = max(raw_intent, key=lambda k: float(raw_intent[k]))
        raw_intent = best

    # List: ["employment_law", "contract_analysis"]
    if isinstance(raw_intent, list):
        if not raw_intent:
            return DEFAULT_INTENT
        raw_intent = raw_intent[0]

    # Normalise string
    candidate = str(raw_intent).strip().lower().replace(" ", "_").replace("-", "_")

    if candidate in VALID_INTENTS:
        return candidate

    # Partial match — e.g. "tenant" → "tenant_rights"
    for valid in VALID_INTENTS:
        if candidate in valid or valid in candidate:
            logger.info(
                f"[Intent] Partial match: '{candidate}' → '{valid}'"
            )
            return valid

    logger.warning(
        f"[Intent] Unknown intent '{candidate}' — defaulting to '{DEFAULT_INTENT}'"
    )
    return DEFAULT_INTENT


# ─────────────────────────────────────────────
# SAFE JSON PARSER
# ─────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove markdown code fences."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$",           "", text).strip()
    return text


def _remove_trailing_commas(text: str) -> str:
    """
    Remove trailing commas before } or ] which are invalid JSON
    but common in LLM output.
    e.g.  {"a": 1,}  →  {"a": 1}
    """
    # Trailing comma before closing brace/bracket
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    Find the first complete {...} block in text.
    Handles extra prose before/after the JSON.
    Uses bracket counting — more reliable than regex for nested JSON.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth   = 0
    in_str  = False
    escape  = False

    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]

    return None


def _recover_truncated_json(text: str) -> Optional[str]:
    """
    Attempt to close a truncated JSON object by counting
    unclosed braces and brackets and appending the needed closers.
    """
    # Remove any incomplete trailing key-value pair
    # e.g.  ..., "key": "unfinished   →  remove it
    text = re.sub(r',?\s*"[^"]*"\s*:\s*"[^"]*$', "", text)
    text = re.sub(r',?\s*"[^"]*"\s*:\s*$',        "", text)
    text = re.sub(r',?\s*"[^"]*"\s*$',             "", text)

    # Count unclosed braces and brackets
    depth_brace   = 0
    depth_bracket = 0
    in_str        = False
    escape        = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth_brace   += 1
        elif ch == "}":
            depth_brace   -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1

    # Append closing tokens in reverse nesting order
    closing = ("]" * max(0, depth_bracket)) + ("}" * max(0, depth_brace))

    if closing:
        return text + closing

    return text


def safe_parse_json(raw: str, fallback: dict) -> dict:
    """
    Six-strategy JSON extractor for local LLM output.
    Never raises — always returns a valid dict.

    Strategy order:
    1. Direct parse
    2. Strip markdown fences → parse
    3. Remove trailing commas → parse
    4. Extract first { } block (handles prose before/after)
    5. Truncation recovery (close unclosed braces)
    6. Return fallback
    """
    if not raw or not raw.strip():
        logger.warning("[JSON] Empty input to safe_parse_json.")
        return fallback

    attempts = []

    # Strategy 1: direct
    attempts.append(raw.strip())

    # Strategy 2: strip fences
    attempts.append(_strip_fences(raw))

    # Strategy 3: strip fences + remove trailing commas
    attempts.append(_remove_trailing_commas(_strip_fences(raw)))

    # Strategy 4: extract first { } block
    extracted = _extract_first_json_object(_strip_fences(raw))
    if extracted:
        attempts.append(extracted)
        attempts.append(_remove_trailing_commas(extracted))

    # Try all collected candidates
    for i, candidate in enumerate(attempts):
        if not candidate or not candidate.strip():
            continue
        try:
            result = json.loads(candidate)
            if i > 0:
                logger.info(f"[JSON] Parsed on strategy {i + 1}.")
            return result
        except json.JSONDecodeError:
            continue

    # Strategy 5: truncation recovery
    base = extracted or _strip_fences(raw)
    recovered = _recover_truncated_json(base)
    if recovered:
        try:
            result = json.loads(recovered)
            logger.info("[JSON] Parsed via truncation recovery.")
            return result
        except json.JSONDecodeError:
            pass

    logger.warning("[JSON] All strategies failed — using fallback.")
    return fallback


# ─────────────────────────────────────────────
# RESPONSE VALIDATOR
# ─────────────────────────────────────────────

def _is_valid_response(text: str, expect_json: bool) -> bool:
    """
    Check if a model response is usable before accepting it.
    Rejects empty, too-short, or clearly non-JSON responses
    when JSON was expected.
    """
    if not text or not text.strip():
        return False

    # Minimum length gate — truncated responses are useless
    if len(text.strip()) < 50:
        logger.warning(
            f"[LLM] Response too short ({len(text)} chars) — rejected."
        )
        return False

    if expect_json:
        stripped = text.strip()
        # Must contain at least one JSON-like character
        if "{" not in stripped:
            logger.warning(
                "[LLM] Response expected JSON but contains no '{' — rejected."
            )
            return False

        # Quick parse attempt — if it completely fails and is very short,
        # it is probably an explanation rather than JSON
        if len(stripped) < 200:
            try:
                json.loads(_strip_fences(stripped))
            except json.JSONDecodeError:
                logger.warning(
                    "[LLM] Short response failed JSON parse — rejected."
                )
                return False

    return True


# ─────────────────────────────────────────────
# SINGLE MODEL ATTEMPT
# ─────────────────────────────────────────────

def _attempt_ollama(
    prompt:     str,
    model:      str,
    max_tokens: int,
    timeout:    int
) -> Optional[str]:
    """
    Make one non-streaming request to Ollama.
    Returns response text or None on any failure.
    """
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict":    max_tokens,
            "temperature":    0.0,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
            # Stop generation at natural JSON end
            "stop": ["\n\nNote:", "\n\nExplanation:", "```"]
        }
    }

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        return text if text else None

    except requests.exceptions.Timeout:
        logger.warning(f"[LLM] Timeout after {timeout}s on '{model}'.")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning(f"[LLM] Connection error on '{model}'.")
        return None
    except Exception as e:
        logger.warning(f"[LLM] Error on '{model}': {e}")
        return None


# ─────────────────────────────────────────────
# MAIN CALLER WITH ADAPTIVE FALLBACK + RETRY
# ─────────────────────────────────────────────

def _call_ollama(
    prompt:      str,
    max_tokens:  int  = 2048,
    retries:     int  = 3,
    expect_json: bool = False
) -> str:
    """
    Adaptive attempt schedule:
    1. Primary model,  full timeout,     capped tokens
    2. Fallback model, full timeout,     capped tokens
    3. Fallback model, extended timeout, full tokens

    Never retries same model consecutively.
    Validates response before accepting — retries on invalid output.
    Tracks last response to avoid retrying identical failed outputs.
    """
    primary      = settings.LLM_MODEL
    fallback     = settings.LLM_FALLBACK_MODEL
    full_timeout = settings.LLM_TIMEOUT

    token_caps = [
        min(max_tokens, 800),
        min(max_tokens, 800),
        max_tokens
    ]

    schedule = [
        (primary,  full_timeout,     token_caps[0], "primary"),
        (fallback, full_timeout,     token_caps[1], "fallback"),
        (fallback, full_timeout * 2, token_caps[2], "fallback / extended"),
    ]

    last_response = None

    for attempt, (model, timeout, tokens, label) in enumerate(
        schedule[:retries], 1
    ):
        logger.info(
            f"[LLM] Attempt {attempt}/{retries} — "
            f"{label} | {model} | timeout: {timeout}s | tokens: {tokens}"
        )

        raw = _attempt_ollama(prompt, model, tokens, timeout)

        # Skip if identical to a previous failed response
        if raw is not None and raw == last_response:
            logger.warning(
                "[LLM] Response identical to previous failed attempt — skipping."
            )
            raw = None

        if raw is not None:
            last_response = raw

            if _is_valid_response(raw, expect_json):
                if model != primary:
                    logger.info(f"[LLM] Fallback '{model}' succeeded.")
                return raw
            else:
                logger.warning(
                    f"[LLM] Response from '{model}' failed validation — "
                    "retrying next attempt."
                )

        if attempt < retries:
            time.sleep(2)

    raise RuntimeError(
        f"All {retries} LLM attempts failed. "
        f"Primary: {primary} | Fallback: {fallback}. "
        "Check 'ollama list' and 'ollama serve'."
    )


# ─────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────

def call_llm(
    prompt:      str,
    max_tokens:  int  = 2048,
    expect_json: bool = False,
    retries:     int  = 3
) -> str:
    """
    Universal LLM caller with adaptive fallback.
    Injects JSON enforcement when expect_json=True.
    """
    final_prompt = (JSON_ENFORCEMENT + prompt) if expect_json else prompt

    raw = _call_ollama(
        final_prompt,
        max_tokens,
        retries,
        expect_json
    )

    if expect_json:
        raw = _strip_fences(raw)

    return raw


def call_llm_for_json(
    prompt:     str,
    fallback:   dict,
    max_tokens: int = 2048,
    retries:    int = 3
) -> dict:
    """
    Call LLM expecting JSON. Returns parsed dict.
    Never raises — returns fallback on complete failure.
    """
    try:
        raw    = call_llm(prompt, max_tokens, expect_json=True, retries=retries)
        result = safe_parse_json(raw, fallback)
        return result
    except Exception as e:
        logger.error(f"[LLM] call_llm_for_json failed: {e} — using fallback.")
        return fallback


def check_ollama_health() -> dict:
    """Check Ollama server and model availability."""
    try:
        resp      = requests.get(settings.OLLAMA_BASE_URL, timeout=5)
        server_ok = resp.status_code == 200

        models_resp      = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5
        )
        available_models = []
        if models_resp.status_code == 200:
            available_models = [
                m["name"]
                for m in models_resp.json().get("models", [])
            ]

        primary_ok  = any(settings.LLM_MODEL          in m for m in available_models)
        fallback_ok = any(settings.LLM_FALLBACK_MODEL  in m for m in available_models)

        return {
            "ollama_running":     server_ok,
            "primary_model":      settings.LLM_MODEL,
            "fallback_model":     settings.LLM_FALLBACK_MODEL,
            "primary_available":  primary_ok,
            "fallback_available": fallback_ok,
            "available_models":   available_models,
            "timeout_seconds":    settings.LLM_TIMEOUT,
            "status": (
                "ready"         if server_ok and primary_ok  else
                "fallback_only" if server_ok and fallback_ok else
                "model_missing" if server_ok                 else
                "offline"
            )
        }

    except requests.exceptions.ConnectionError:
        return {
            "ollama_running":     False,
            "primary_model":      settings.LLM_MODEL,
            "fallback_model":     settings.LLM_FALLBACK_MODEL,
            "primary_available":  False,
            "fallback_available": False,
            "available_models":   [],
            "status":             "offline"
        }