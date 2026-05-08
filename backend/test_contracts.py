import sys
sys.path.insert(0, ".")

from core.contract import (
    extract_clauses_static,
    analyse_contract,
    format_contract_analysis,
    _build_contract_fallback
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── Sample contract text for testing ──────────

SAMPLE_CONTRACT = """
RENTAL AGREEMENT

This Rental Agreement is entered into between ABC Properties (Landlord)
and John Smith (Tenant) on 1st January 2025.

1. DEPOSIT CLAUSE
The Tenant shall pay a non-refundable security deposit of $5,000
upon signing. This deposit shall be forfeited in its entirety
if the Tenant vacates before the lease term ends.

2. PENALTY CLAUSE
In case of late payment, a penalty of 10% per month shall be charged
on the outstanding amount. Additionally, the Tenant shall pay
liquidated damages of $2,000 for any breach of this agreement.

3. TERMINATION CLAUSE
The Landlord may terminate this agreement without cause and without
notice at sole discretion. The Tenant must vacate within 24 hours
of receiving a termination notice.

4. OBLIGATIONS
The Tenant shall be responsible for all repairs and maintenance costs
regardless of cause. The Tenant undertakes to indemnify and hold
harmless the Landlord for any damages to the property.

5. DISPUTE RESOLUTION
All disputes shall be resolved through arbitration in a jurisdiction
chosen by the Landlord. The Tenant waives all rights to approach
any court of law.

6. CONFIDENTIALITY
The Tenant agrees to keep all terms of this agreement confidential
and shall not disclose any information to third parties.

7. LIMITATION OF LIABILITY
The Landlord's maximum liability under this agreement shall not
exceed $100 under any circumstances.
"""


def test_static_extraction():
    separator("TEST 1 — STATIC CLAUSE EXTRACTION (no LLM)")

    clauses = extract_clauses_static(SAMPLE_CONTRACT)

    total = sum(len(v) for v in clauses.values())
    print(f"Total sentences matched: {total}\n")

    for clause_type, sentences in clauses.items():
        if sentences:
            print(f"[{clause_type.upper()}] — {len(sentences)} found")
            for s in sentences[:2]:
                print(f"  → {s[:120]}...")
            print()

    assert total > 0, "Static extractor found nothing!"
    print("✅ Static extraction passed.")


def test_static_only_analysis():
    separator("TEST 2 — FULL STATIC ANALYSIS (no LLM)")

    analysis = analyse_contract(
        contract_text=SAMPLE_CONTRACT,
        filename="test_rental.txt",
        use_llm=False
    )

    print(f"Overall Risk   : {analysis['overall_risk_display']} "
          f"(score: {analysis['overall_risk_score']})")
    print(f"Recommendation : {analysis['recommendation_display']}")
    print(f"Total Clauses  : {analysis['clause_count']}")
    print(f"  Unfair : {analysis['unfair_count']}")
    print(f"  Risky  : {analysis['risky_count']}")
    print(f"  Safe   : {analysis['safe_count']}")

    print(f"\nSummary:\n  {analysis['summary']}")

    if analysis["critical_issues"]:
        print(f"\nCritical Issues:")
        for issue in analysis["critical_issues"]:
            print(f"  🚨 {issue[:100]}")

    print(f"\nClauses:")
    for c in analysis["clauses"][:5]:
        print(
            f"  {c['risk_display']:15} | {c['type']:25} | "
            f"score: {c['risk_score']:3} | {c['title']}"
        )

    assert analysis["clause_count"] > 0, "No clauses found!"
    print("\n✅ Static analysis passed.")


def test_llm_analysis():
    separator("TEST 3 — LLM ANALYSIS (1 Gemini call)")

    print("Sending to Gemini 2.5 Flash...\n")

    analysis = analyse_contract(
        contract_text=SAMPLE_CONTRACT,
        filename="test_rental.txt",
        use_llm=True
    )

    print(f"Overall Risk   : {analysis['overall_risk_display']} "
          f"(score: {analysis['overall_risk_score']})")
    print(f"Recommendation : {analysis['recommendation_display']}")
    print(f"Reason         : {analysis['recommendation_reason']}")
    print(f"Total Clauses  : {analysis['clause_count']}")
    print(f"  Unfair : {analysis['unfair_count']}")
    print(f"  Risky  : {analysis['risky_count']}")
    print(f"  Safe   : {analysis['safe_count']}")

    print(f"\nSummary:\n  {analysis['summary']}")

    if analysis["critical_issues"]:
        print(f"\nCritical Issues:")
        for issue in analysis["critical_issues"][:3]:
            print(f"  🚨 {issue[:120]}")

    if analysis["positive_aspects"]:
        print(f"\nPositive Aspects:")
        for aspect in analysis["positive_aspects"]:
            print(f"  ✅ {aspect[:120]}")

    print(f"\nAll Clauses:")
    for c in analysis["clauses"]:
        print(
            f"  {c['risk_display']:15} | score: {c['risk_score']:3} | "
            f"{c['type']:30} | {c['title']}"
        )

    assert analysis["clause_count"] > 0, "LLM returned no clauses!"
    print("\n✅ LLM analysis passed.")


if __name__ == "__main__":
    print("\n⚖️  CONTRACT ANALYSIS SYSTEM — TEST")

    test_static_extraction()
    test_static_only_analysis()

    run_llm = input(
        "\nRun LLM test? Uses 1 Gemini API call. (y/n): "
    ).strip().lower()

    if run_llm == "y":
        test_llm_analysis()
    else:
        print("Skipping LLM test.")

    print("\n✅ ALL CONTRACT TESTS COMPLETE")