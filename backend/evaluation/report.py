"""Reporting helpers for evaluation results."""
import json
import os
from datetime import datetime
from typing import Dict
from tabulate import tabulate
from colorama import Fore, Style, init

init(autoreset=True)

REPORT_DIR = os.path.join("evaluation", "reports")


# ─────────────────────────────────────────────
# COLOUR HELPERS
# ─────────────────────────────────────────────

def _colour_score(score: float) -> str:
    val = f"{score:.3f}"
    if score >= 0.8:
        return Fore.GREEN  + val + Style.RESET_ALL
    if score >= 0.6:
        return Fore.YELLOW + val + Style.RESET_ALL
    return Fore.RED + val + Style.RESET_ALL


def _colour_pass(passed: bool) -> str:
    return (
        Fore.GREEN  + "✅ PASS" + Style.RESET_ALL
        if passed else
        Fore.RED    + "❌ FAIL" + Style.RESET_ALL
    )


def _colour_risk(risk: str) -> str:
    colours = {
        "none":   Fore.GREEN,
        "low":    Fore.GREEN,
        "medium": Fore.YELLOW,
        "high":   Fore.RED
    }
    return colours.get(risk, Fore.WHITE) + risk.upper() + Style.RESET_ALL


def _colour_grade(grade: str) -> str:
    colours = {
        "A": Fore.GREEN,
        "B": Fore.CYAN,
        "C": Fore.YELLOW,
        "D": Fore.MAGENTA,
        "F": Fore.RED
    }
    return colours.get(grade, Fore.WHITE) + grade + Style.RESET_ALL


# ─────────────────────────────────────────────
# CONSOLE REPORT
# ─────────────────────────────────────────────

def print_console_report(eval_result: Dict):
    """Print a formatted evaluation report to the terminal."""
    summary = eval_result["summary"]
    h_sum   = eval_result["hallucination_summary"]
    cat_sum = eval_result["category_breakdown"]
    comp    = eval_result["component_accuracy"]
    results = eval_result["individual_results"]

    print("\n" + "=" * 70)
    print("  ⚖️  LEGAL INTELLIGENCE SYSTEM — EVALUATION REPORT")
    print(f"  Generated: {datetime.now().strftime('%d %B %Y %H:%M:%S')}")
    print("=" * 70)

    # ── Overall Summary ───────────────────────
    print(f"\n{'─'*70}")
    print("  OVERALL SUMMARY")
    print(f"{'─'*70}")
    print(f"  Grade           : {_colour_grade(summary['grade'])}")
    print(f"  Overall Score   : {_colour_score(summary['avg_score'])}")
    print(f"  Pass Rate       : {summary['pass_rate']} "
          f"({summary['pass_percentage']}%)")
    print(f"  Errors          : {summary['errors']}")
    print(f"  Avg Latency     : {summary['avg_latency_seconds']}s per query")

    # ── Hallucination Summary ─────────────────
    print(f"\n{'─'*70}")
    print("  HALLUCINATION ANALYSIS")
    print(f"{'─'*70}")
    print(f"  Safe Responses  : {h_sum['safe_count']} / "
          f"{h_sum['safe_rate'].split('/')[1] if '/' in h_sum.get('safe_rate','0/0') else '?'}")
    print(f"  High Risk       : {Fore.RED}{h_sum['high_risk_count']}{Style.RESET_ALL}")
    print(f"  Medium Risk     : {Fore.YELLOW}{h_sum['medium_risk_count']}{Style.RESET_ALL}")

    # ── Category Breakdown ────────────────────
    print(f"\n{'─'*70}")
    print("  CATEGORY BREAKDOWN")
    print(f"{'─'*70}")
    cat_rows = [
        [
            cat,
            data["pass_rate"],
            _colour_score(data["avg_score"])
        ]
        for cat, data in cat_sum.items()
    ]
    print(tabulate(
        cat_rows,
        headers=["Category", "Pass Rate", "Avg Score"],
        tablefmt="simple"
    ))

    # ── Component Accuracy ────────────────────
    print(f"\n{'─'*70}")
    print("  COMPONENT ACCURACY")
    print(f"{'─'*70}")
    comp_rows = [
        [k.replace("_", " ").title(), _colour_score(v)]
        for k, v in sorted(comp.items(), key=lambda x: x[1])
    ]
    print(tabulate(
        comp_rows,
        headers=["Component", "Accuracy"],
        tablefmt="simple"
    ))

    # ── Individual Results ────────────────────
    print(f"\n{'─'*70}")
    print("  INDIVIDUAL TEST RESULTS")
    print(f"{'─'*70}")
    rows = []
    for r in results:
        h_risk = r.get("hallucination", {}).get("hallucination_risk", "?")
        rows.append([
            r["test_id"],
            r["category"][:15],
            r["query"][:40] + "..." if len(r["query"]) > 40 else r["query"],
            _colour_score(r["overall_score"]),
            _colour_pass(r.get("passed", False)),
            _colour_risk(h_risk),
            f"{r['latency_seconds']}s"
        ])

    print(tabulate(
        rows,
        headers=[
            "ID", "Category", "Query",
            "Score", "Result", "Halluc. Risk", "Latency"
        ],
        tablefmt="simple"
    ))

    # ── Failed Cases ──────────────────────────
    failed = [r for r in results if not r.get("passed", True)]
    if failed:
        print(f"\n{'─'*70}")
        print(f"  FAILED CASES ({len(failed)})")
        print(f"{'─'*70}")
        for r in failed:
            print(f"\n  [{r['test_id']}] {r['query'][:60]}")
            if "error" in r:
                print(f"    Error: {r['error']}")
            else:
                for comp_name, comp_data in r.get("components", {}).items():
                    if not comp_data.get("passed"):
                        print(
                            f"    ❌ {comp_name:20} → "
                            f"{comp_data.get('detail','')[:60]}"
                        )

    print(f"\n{'='*70}")
    print(f"  END OF REPORT")
    print(f"{'='*70}\n")


# ─────────────────────────────────────────────
# JSON REPORT SAVER
# ─────────────────────────────────────────────

def save_json_report(eval_result: Dict) -> str:
    """Save evaluation result as JSON file. Returns file path."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"eval_report_{timestamp}.json"
    filepath  = os.path.join(REPORT_DIR, filename)

    # Remove non-serialisable fields
    clean_result = json.loads(json.dumps(eval_result, default=str))

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean_result, f, indent=2, ensure_ascii=False)

    return filepath


# ─────────────────────────────────────────────
# ACCURACY TRACKER
# ─────────────────────────────────────────────

def load_history() -> list:
    """Load all previous evaluation reports for trend tracking."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    history = []

    for fname in sorted(os.listdir(REPORT_DIR)):
        if fname.endswith(".json"):
            fpath = os.path.join(REPORT_DIR, fname)
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                    history.append({
                        "file":             fname,
                        "avg_score":        data["summary"]["avg_score"],
                        "pass_percentage":  data["summary"]["pass_percentage"],
                        "grade":            data["summary"]["grade"],
                        "hallucination_high": data["hallucination_summary"]["high_risk_count"]
                    })
            except Exception:
                continue

    return history


def print_accuracy_trend():
    """Print historical accuracy trend from saved reports."""
    history = load_history()

    if not history:
        print("  No previous evaluation reports found.")
        return

    print(f"\n{'─'*60}")
    print("  ACCURACY TREND (historical)")
    print(f"{'─'*60}")

    rows = [
        [
            h["file"].replace("eval_report_", "").replace(".json", ""),
            _colour_score(h["avg_score"]),
            f"{h['pass_percentage']}%",
            _colour_grade(h["grade"]),
            h["hallucination_high"]
        ]
        for h in history[-10:]  # last 10 runs
    ]

    print(tabulate(
        rows,
        headers=["Run", "Avg Score", "Pass %", "Grade", "High Halluc."],
        tablefmt="simple"
    ))