"""
Legal Intelligence System — Evaluation Runner
Usage:
  python run_eval.py                    # run all tests
  python run_eval.py --category tenant_rights
  python run_eval.py --ids TR-001 CT-001
  python run_eval.py --save             # save JSON report
  python run_eval.py --trend            # show historical trend
  python run_eval.py --static           # score without API (hallucination only)
  python run_eval.py --delay 3          # 3s delay between calls
"""
import sys
import argparse
sys.path.insert(0, ".")

from evaluation.eval_runner import run_evaluation
from evaluation.report import (
    print_console_report,
    save_json_report,
    print_accuracy_trend
)
from evaluation.hallucination_detector import analyse_hallucination_risk
from utils.logger import logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Legal Intelligence System — Evaluation"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Run only cases from this category"
    )
    parser.add_argument(
        "--ids", nargs="+", default=None,
        help="Run specific test case IDs e.g. TR-001 CT-002"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save JSON report to evaluation/reports/"
    )
    parser.add_argument(
        "--trend", action="store_true",
        help="Show historical accuracy trend"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds to wait between API calls (default 2.0)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("\n⚖️  Legal Intelligence System — Evaluation Framework")
    print(f"   Server : http://localhost:8000")
    print(f"   Delay  : {args.delay}s between calls\n")

    if args.trend:
        print_accuracy_trend()
        return

    # Check server is up
    try:
        import requests
        resp = requests.get("http://localhost:8000/api/health", timeout=5)
        if resp.status_code != 200:
            print("❌ Server health check failed. Is uvicorn running?")
            sys.exit(1)
        print("✅ Server is running.\n")
    except Exception:
        print("❌ Cannot reach server at http://localhost:8000.")
        print("   Start it with: uvicorn main:app --reload")
        sys.exit(1)

    # Run evaluation
    eval_result = run_evaluation(
        category      = args.category,
        ids           = args.ids,
        delay_seconds = args.delay
    )

    # Print report
    print_console_report(eval_result)

    # Save report
    if args.save:
        path = save_json_report(eval_result)
        print(f"\n💾 Report saved to: {path}")

    # Exit code based on pass rate
    pct = eval_result["summary"]["pass_percentage"]
    sys.exit(0 if pct >= 60 else 1)


if __name__ == "__main__":
    main()