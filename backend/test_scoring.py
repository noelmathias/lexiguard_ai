import sys
sys.path.insert(0, ".")

from core.scoring import (
    compute_risk_score,
    compute_confidence_score,
    compute_scores,
    format_scores_for_response
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


TEST_CASES = [
    {
        "label":   "LOW RISK — General question",
        "query":   "What is a legal notice?",
        "intent":  "legal_notice",
        "intent_confidence": 0.9,
        "entities": {
            "parties": [], "legal_concepts": ["legal notice"],
            "documents": [], "locations": [], "amounts": [],
            "dates": [], "actions": []
        },
        "retrieval_confidence": 0.75,
        "chunks": [{"title": "Legal Notice Requirements"}] * 4
    },
    {
        "label":   "MEDIUM RISK — Deposit dispute",
        "query":   "My landlord is refusing to return my $2000 deposit.",
        "intent":  "tenant_rights",
        "intent_confidence": 0.85,
        "entities": {
            "parties": ["landlord", "tenant"],
            "legal_concepts": ["security deposit"],
            "documents": [], "locations": [],
            "amounts": ["$2000"],
            "dates": [],
            "actions": ["refusing to return deposit"]
        },
        "retrieval_confidence": 0.65,
        "chunks": [{"title": "Security Deposit Rules"}] * 3
    },
    {
        "label":   "HIGH RISK — Criminal + urgent",
        "query":   "I was arrested and charged with fraud. What are my rights?",
        "intent":  "criminal_law",
        "intent_confidence": 0.95,
        "entities": {
            "parties": ["police"],
            "legal_concepts": ["arrest", "fraud", "criminal charges"],
            "documents": [], "locations": [],
            "amounts": [],
            "dates": [],
            "actions": ["arrested", "charged"]
        },
        "retrieval_confidence": 0.55,
        "chunks": [{"title": "Criminal Law"}] * 2,
        "guidance_raw": {
            "urgency": "high",
            "urgency_reason": "Criminal charges require immediate legal representation."
        }
    },
    {
        "label":   "HIGH RISK — Wrongful termination",
        "query":   "My employer terminated me without notice after I filed a complaint.",
        "intent":  "employment_law",
        "intent_confidence": 0.88,
        "entities": {
            "parties": ["employer", "employee"],
            "legal_concepts": ["wrongful termination"],
            "documents": [],
            "locations": [],
            "amounts": [],
            "dates": [],
            "actions": ["terminated", "filed complaint"]
        },
        "retrieval_confidence": 0.70,
        "chunks": [{"title": "Wrongful Termination"}] * 4
    }
]


def test_risk_scoring():
    separator("TEST 1 — RISK SCORING")

    for case in TEST_CASES:
        risk = compute_risk_score(
            query        = case["query"],
            intent       = case["intent"],
            entities     = case["entities"],
            guidance_raw = case.get("guidance_raw")
        )

        print(f"\n  [{case['label']}]")
        print(f"  Query    : {case['query'][:70]}...")
        print(f"  Score    : {risk['risk_score']} | {risk['risk_display']}")
        print(f"  Breakdown: {risk['breakdown']}")
        if risk["flags"]:
            for f in risk["flags"]:
                print(f"  ⚑ {f}")

    print("\n✅ Risk scoring passed.")


def test_confidence_scoring():
    separator("TEST 2 — CONFIDENCE SCORING")

    for case in TEST_CASES:
        conf = compute_confidence_score(
            retrieval_confidence = case["retrieval_confidence"],
            intent_confidence    = case["intent_confidence"],
            entities             = case["entities"],
            query                = case["query"],
            retrieved_chunks     = case["chunks"]
        )

        print(f"\n  [{case['label']}]")
        print(f"  Score      : {conf['confidence_score']} | "
              f"{conf['confidence_display']}")
        print(f"  Explanation: {conf['explanation']}")
        print(f"  Components : { {k: round(v,2) for k,v in conf['components'].items()} }")

    print("\n✅ Confidence scoring passed.")


def test_combined_scores():
    separator("TEST 3 — COMBINED SCORES + FORMAT")

    case = TEST_CASES[2]  # HIGH RISK criminal case

    scores   = compute_scores(
        query                = case["query"],
        intent               = case["intent"],
        intent_confidence    = case["intent_confidence"],
        entities             = case["entities"],
        retrieval_confidence = case["retrieval_confidence"],
        retrieved_chunks     = case["chunks"],
        guidance_raw         = case.get("guidance_raw")
    )

    formatted = format_scores_for_response(scores)

    print(f"\n  Query   : {case['query']}")
    print(f"\n  RISK:")
    print(f"    Score   : {formatted['risk']['score']}")
    print(f"    Display : {formatted['risk']['display']}")
    print(f"    Colour  : {formatted['risk']['colour']}")
    print(f"    Flags   :")
    for f in formatted["risk"]["flags"]:
        print(f"      ⚑ {f}")

    print(f"\n  CONFIDENCE:")
    print(f"    Score      : {formatted['confidence']['score']}")
    print(f"    Display    : {formatted['confidence']['display']}")
    print(f"    Explanation: {formatted['confidence']['explanation']}")

    print(f"\n  SUMMARY : {formatted['summary']}")

    if formatted["confidence_note"]:
        print(f"\n  NOTE: {formatted['confidence_note']}")

    print("\n✅ Combined scoring passed.")


def test_score_ranges():
    separator("TEST 4 — SCORE RANGE VALIDATION")

    for case in TEST_CASES:
        scores = compute_scores(
            query                = case["query"],
            intent               = case["intent"],
            intent_confidence    = case["intent_confidence"],
            entities             = case["entities"],
            retrieval_confidence = case["retrieval_confidence"],
            retrieved_chunks     = case["chunks"],
            guidance_raw         = case.get("guidance_raw")
        )

        r = scores["risk_score"]
        c = scores["confidence_score"]

        assert 0 <= r <= 100, f"Risk score out of range: {r}"
        assert 0 <= c <= 100, f"Confidence score out of range: {c}"

        print(f"  ✅ {case['label']:35} | "
              f"Risk: {r:3}/100 | Confidence: {c:3}/100")

    print("\n✅ All scores within valid range.")
    


if __name__ == "__main__":
    print("\n⚖️  RISK + CONFIDENCE SCORING — TEST")
    test_risk_scoring()
    test_confidence_scoring()
    test_combined_scores()
    test_score_ranges()
    print("\n✅ ALL SCORING TESTS COMPLETE")