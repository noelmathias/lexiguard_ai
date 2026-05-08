import sys
sys.path.insert(0, ".")

from core.comparison import (
    compare_contracts,
    _diff_clauses_static,
    extract_clauses_static
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── Sample contracts ──────────────────────────

CONTRACT_A = """
RENTAL AGREEMENT — VERSION A

1. DEPOSIT
Tenant shall pay a refundable security deposit of $1,000.
The deposit will be returned within 14 days of vacating
minus documented deductions for damage.

2. PENALTY
Late payment incurs a fee of $50 per week after a 5-day
grace period.

3. TERMINATION
Either party may terminate with 30 days written notice.
Landlord may terminate for non-payment after 7-day notice.

4. OBLIGATIONS
Landlord shall maintain the property in habitable condition.
Tenant shall not sublet without written consent.

5. DISPUTE RESOLUTION
Disputes shall be resolved by mediation before litigation.
Governing law: State of California.
"""

CONTRACT_B = """
RENTAL AGREEMENT — VERSION B

1. DEPOSIT
Tenant shall pay a NON-REFUNDABLE deposit of $3,000.
This deposit is forfeited in full if tenant vacates
for any reason before lease expiry.

2. PENALTY
Late payment incurs a penalty of 15% per month compounding.
Liquidated damages of $5,000 apply for any breach.

3. TERMINATION
Landlord may terminate without cause at sole discretion.
Tenant must vacate within 24 hours of notice.

4. OBLIGATIONS
Tenant is responsible for ALL maintenance and repairs.
Tenant shall indemnify landlord for any property damage.

5. DISPUTE RESOLUTION
All disputes resolved by arbitration chosen by Landlord.
Tenant waives right to any court proceedings.

6. LIMITATION OF LIABILITY
Landlord's total liability shall not exceed $50.
"""


def test_static_diff():
    separator("TEST 1 — STATIC CLAUSE DIFF (no LLM)")

    clauses_a = extract_clauses_static(CONTRACT_A)
    clauses_b = extract_clauses_static(CONTRACT_B)

    diffs = _diff_clauses_static(clauses_a, clauses_b)

    print(f"Clause types compared: {len(diffs)}\n")
    for d in diffs:
        print(
            f"  [{d['diff_type'].upper():8}] "
            f"{d['clause_type']:25} | "
            f"similarity: {d['similarity']:.2f}"
        )
        print(f"           → {d['change_summary']}")

    assert len(diffs) > 0, "No differences found!"
    print("\n✅ Static diff passed.")


def test_static_comparison():
    separator("TEST 2 — FULL STATIC COMPARISON (no LLM)")

    result = compare_contracts(
        text_a  = CONTRACT_A,
        text_b  = CONTRACT_B,
        name_a  = "Version A (Tenant-Friendly)",
        name_b  = "Version B (Landlord-Heavy)",
        use_llm = False
    )

    print(f"Document A Risk : {result['overall_risk_display_a']} "
          f"({result['overall_risk_score_a']})")
    print(f"Document B Risk : {result['overall_risk_display_b']} "
          f"({result['overall_risk_score_b']})")
    print(f"Riskier         : {result['riskier_display']}")
    print(f"Recommendation  : {result['recommendation_display']}")
    print(f"Clauses compared: {result['total_clauses_compared']}")
    print(f"High severity   : {result['high_severity_count']}")

    print(f"\nComparison Table:")
    for row in result["comparison_table"][:5]:
        print(
            f"  Row {row['row_number']:2} | "
            f"{row['clause_title']:25} | "
            f"A: {row['risk_display_a']:12} | "
            f"B: {row['risk_display_b']:12} | "
            f"{row['severity_display']}"
        )

    if result["key_differences"]:
        print(f"\nKey Differences:")
        for d in result["key_differences"]:
            print(f"  • {d}")

    assert result["total_clauses_compared"] > 0, "No clauses compared!"
    print("\n✅ Static comparison passed.")


def test_llm_comparison():
    separator("TEST 3 — LLM COMPARISON (1 Gemini call)")

    print("Sending to Gemini 2.5 Flash...\n")

    result = compare_contracts(
        text_a  = CONTRACT_A,
        text_b  = CONTRACT_B,
        name_a  = "Version A (Tenant-Friendly)",
        name_b  = "Version B (Landlord-Heavy)",
        use_llm = True
    )

    print(f"Document A Risk  : {result['overall_risk_display_a']} "
          f"(score: {result['overall_risk_score_a']})")
    print(f"Document B Risk  : {result['overall_risk_display_b']} "
          f"(score: {result['overall_risk_score_b']})")
    print(f"Riskier          : {result['riskier_display']}")
    print(f"Recommendation   : {result['recommendation_display']}")
    print(f"Reason           : {result['recommendation_reason']}")
    print(f"Clauses compared : {result['total_clauses_compared']}")
    print(f"High severity    : {result['high_severity_count']}")

    print(f"\nComparison Table:")
    for row in result["comparison_table"]:
        print(
            f"  {row['clause_title']:28} | "
            f"A: {row['risk_display_a']:12} ({row['risk_score_a']:3}) | "
            f"B: {row['risk_display_b']:12} ({row['risk_score_b']:3}) | "
            f"{row['severity_display']:12} | "
            f"{row['favours_display']}"
        )

    if result["key_differences"]:
        print(f"\nKey Differences:")
        for d in result["key_differences"]:
            print(f"  • {d}")

    if result["advantages_a"]:
        print(f"\nAdvantages of Version A:")
        for a in result["advantages_a"]:
            print(f"  ✅ {a}")

    if result["advantages_b"]:
        print(f"\nAdvantages of Version B:")
        for a in result["advantages_b"]:
            print(f"  ⚠️  {a}")

    if result["high_severity_clauses"]:
        print(f"\nHigh Severity Clauses:")
        for c in result["high_severity_clauses"]:
            print(f"  🔴 {c['clause_title']}: {c['difference']}")

    assert result["total_clauses_compared"] > 0, "No clauses in LLM result!"
    print("\n✅ LLM comparison passed.")


if __name__ == "__main__":
    print("\n⚖️  COMPARISON ENGINE — TEST")

    test_static_diff()
    test_static_comparison()

    run_llm = input(
        "\nRun LLM test? Uses 1 Gemini API call. (y/n): "
    ).strip().lower()

    if run_llm == "y":
        test_llm_comparison()
    else:
        print("Skipping LLM test.")

    print("\n✅ ALL COMPARISON TESTS COMPLETE")