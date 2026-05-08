"""Entrypoints for running evaluation workflows."""
import time
import requests
from typing import Dict, List, Optional
from utils.logger import logger
from evaluation.test_dataset import TEST_CASES, get_test_cases
from evaluation.metrics import score_test_case
from evaluation.hallucination_detector import analyse_hallucination_risk


# ─────────────────────────────────────────────
# API CALLER
# ─────────────────────────────────────────────

BASE_URL = "http://localhost:8000/api"


def call_query_api(query: str, timeout: int = 120) -> Optional[Dict]:
    """Call the /api/query endpoint and return response dict."""
    try:
        resp = requests.post(
            f"{BASE_URL}/query",
            json={"query": query, "chat_history": []},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(
                f"API returned {resp.status_code} for query: {query[:50]}"
            )
            return None
    except requests.exceptions.Timeout:
        logger.error(f"API timeout for query: {query[:50]}")
        return None
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return None


# ─────────────────────────────────────────────
# SINGLE CASE RUNNER
# ─────────────────────────────────────────────

def run_single_case(test_case: Dict) -> Dict:
    """
    Run a single test case through the API and score it.
    Returns full result dict.
    """
    logger.info(
        f"[Eval] Running {test_case['id']} — {test_case['query'][:50]}..."
    )

    start_time = time.time()
    response   = call_query_api(test_case["query"])
    latency    = round(time.time() - start_time, 2)

    if response is None:
        return {
            "test_id":        test_case["id"],
            "category":       test_case["category"],
            "query":          test_case["query"],
            "overall_score":  0.0,
            "passed":         False,
            "pass_rate":      "0/8",
            "error":          "API call failed or timed out",
            "latency_seconds": latency,
            "components":     {},
            "hallucination":  {},
            "actual":         {}
        }

    # Score the response
    scores = score_test_case(test_case, response)

    # Hallucination analysis
    answer         = response.get("answer", "")
    hallucination  = analyse_hallucination_risk(answer)

    return {
        **scores,
        "latency_seconds":  latency,
        "hallucination":    hallucination,
        "api_response":     {
            "intent":     response.get("intent"),
            "confidence": response.get("confidence"),
            "risk_score": response.get("risk_score"),
            "guardrails": response.get("guardrails", {})
        }
    }


# ─────────────────────────────────────────────
# FULL EVAL RUNNER
# ─────────────────────────────────────────────

def run_evaluation(
    category:      str  = None,
    ids:           list = None,
    delay_seconds: float = 2.0
) -> Dict:
    """
    Run evaluation on all or filtered test cases.
    delay_seconds: pause between API calls (avoids rate limits).

    Returns aggregated evaluation result dict.
    """
    cases   = get_test_cases(category=category, ids=ids)
    results = []

    logger.info(
        f"[Eval] Starting evaluation — {len(cases)} test cases | "
        f"delay: {delay_seconds}s between calls"
    )

    for i, case in enumerate(cases):
        result = run_single_case(case)
        results.append(result)

        logger.info(
            f"[Eval] {case['id']} — "
            f"score: {result['overall_score']} | "
            f"passed: {result['passed']} | "
            f"latency: {result['latency_seconds']}s"
        )

        # Delay between calls
        if i < len(cases) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)

    return aggregate_results(results)


# ─────────────────────────────────────────────
# AGGREGATOR
# ─────────────────────────────────────────────

def aggregate_results(results: List[Dict]) -> Dict:
    """Aggregate individual test results into summary metrics."""

    total       = len(results)
    passed      = sum(1 for r in results if r.get("passed", False))
    errors      = sum(1 for r in results if "error" in r)
    scores      = [r["overall_score"] for r in results if "error" not in r]

    avg_score   = round(sum(scores) / len(scores), 3) if scores else 0.0
    avg_latency = round(
        sum(r["latency_seconds"] for r in results) / total, 2
    ) if total else 0.0

    # Per-category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "scores": []}
        categories[cat]["total"]  += 1
        categories[cat]["passed"] += 1 if r.get("passed") else 0
        if "error" not in r:
            categories[cat]["scores"].append(r["overall_score"])

    category_summary = {}
    for cat, data in categories.items():
        avg = round(
            sum(data["scores"]) / len(data["scores"]), 3
        ) if data["scores"] else 0.0
        category_summary[cat] = {
            "total":      data["total"],
            "passed":     data["passed"],
            "pass_rate":  f"{data['passed']}/{data['total']}",
            "avg_score":  avg
        }

    # Hallucination summary
    h_results = [r["hallucination"] for r in results if r.get("hallucination")]
    h_high    = sum(1 for h in h_results if h.get("hallucination_risk") == "high")
    h_medium  = sum(1 for h in h_results if h.get("hallucination_risk") == "medium")
    h_safe    = sum(1 for h in h_results if h.get("safe", True))

    # Component accuracy across all cases
    component_totals  = {}
    component_counts  = {}
    for r in results:
        for comp, data in r.get("components", {}).items():
            component_totals[comp]  = component_totals.get(comp, 0) + data["score"]
            component_counts[comp]  = component_counts.get(comp, 0) + 1

    component_accuracy = {
        k: round(component_totals[k] / component_counts[k], 3)
        for k in component_totals
    }

    # Grade
    grade = (
        "A" if avg_score >= 0.85 else
        "B" if avg_score >= 0.70 else
        "C" if avg_score >= 0.55 else
        "D" if avg_score >= 0.40 else
        "F"
    )

    return {
        "summary": {
            "total_cases":         total,
            "passed":              passed,
            "failed":              total - passed - errors,
            "errors":              errors,
            "pass_rate":           f"{passed}/{total}",
            "pass_percentage":     round((passed / total) * 100, 1) if total else 0,
            "avg_score":           avg_score,
            "avg_latency_seconds": avg_latency,
            "grade":               grade
        },
        "hallucination_summary": {
            "high_risk_count":   h_high,
            "medium_risk_count": h_medium,
            "safe_count":        h_safe,
            "safe_rate":         f"{h_safe}/{len(h_results)}" if h_results else "N/A"
        },
        "category_breakdown":    category_summary,
        "component_accuracy":    component_accuracy,
        "individual_results":    results
    }