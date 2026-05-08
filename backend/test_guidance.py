import sys
import json
sys.path.insert(0, ".")

from core.rag import rag_system
from core.agents import run_agent_pipeline
from core.guidance import (
    generate_legal_guidance,
    format_guidance_for_response,
    STATIC_GUIDANCE,
    INTENT_DOMAIN_MAP
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_static_fallback():
    separator("TEST 1 — STATIC FALLBACK LIBRARY")
    for intent in list(STATIC_GUIDANCE.keys())[:3]:
        s = STATIC_GUIDANCE[intent]
        print(f"\nIntent : {intent}")
        print(f"Domain : {INTENT_DOMAIN_MAP.get(intent)}")
        print(f"Rights : {len(s['rights'])} items")
        print(f"Steps  : {len(s['steps'])} items")
        print(f"Docs   : {len(s['documents'])} items")
    print("\n✅ Static library intact.")


def test_guidance_generation():
    separator("TEST 2 — GUIDANCE GENERATION (LLM)")

    rag_system.initialise()

    test_cases = [
        {
            "query":   "My landlord won't fix the heating and it's winter.",
            "intent":  "tenant_rights",
            "entities": {
                "parties":        ["landlord", "tenant"],
                "legal_concepts": ["habitability", "repair obligation"],
                "amounts":        [],
                "actions":        ["refused repairs"],
                "documents":      [],
                "locations":      [],
                "dates":          []
            }
        },
        {
            "query":   "I was fired after reporting safety violations at work.",
            "intent":  "employment_law",
            "entities": {
                "parties":        ["employer", "employee"],
                "legal_concepts": ["wrongful termination", "whistleblower protection"],
                "amounts":        [],
                "actions":        ["fired", "reported violations"],
                "documents":      [],
                "locations":      [],
                "dates":          []
            }
        }
    ]

    for case in test_cases:
        print(f"\n--- Query: {case['query']} ---")

        retrieval = rag_system.retrieve(case["query"], top_k=3)

        guidance_raw = generate_legal_guidance(
            query=case["query"],
            intent=case["intent"],
            entities=case["entities"],
            context=retrieval["context"]
        )

        guidance = format_guidance_for_response(guidance_raw)

        print(f"Domain   : {guidance['legal_domain']}")
        print(f"Urgency  : {guidance['urgency_display']}")
        print(f"Reason   : {guidance['urgency_reason']}")

        print(f"\nRights ({len(guidance['rights'])}):")
        for r in guidance["rights"][:3]:
            print(f"  {r['id']}. {r['description']}")

        print(f"\nSteps ({len(guidance['steps'])}):")
        for s in guidance["steps"][:3]:
            print(f"  Step {s['step']}: {s['action']}")

        print(f"\nDocuments ({len(guidance['documents'])}):")
        for d in guidance["documents"][:3]:
            print(f"  {d['id']}. {d['document']}")

        if guidance["time_limit_warning"]:
            print(f"\n⚠️  Time Limit: {guidance['time_limit_warning']}")


def test_full_pipeline_with_guidance():
    separator("TEST 3 — FULL PIPELINE WITH GUIDANCE")

    query = "My landlord is threatening to evict me without proper notice."
    rag_system.initialise()
    retrieval = rag_system.retrieve(query, top_k=5)

    result = run_agent_pipeline(
        query=query,
        context=retrieval["context"],
        confidence=retrieval["confidence"],
        chunks=retrieval["chunks"]
    )

    guidance_raw = generate_legal_guidance(
        query=query,
        intent=result["intent"],
        entities=result["entities"],
        context=retrieval["context"]
    )
    guidance = format_guidance_for_response(guidance_raw)

    print(f"\nIntent   : {result['intent']}")
    print(f"Urgency  : {guidance['urgency_display']}")
    print(f"Rights   : {len(guidance['rights'])} items")
    print(f"Steps    : {len(guidance['steps'])} items")
    print(f"Docs     : {len(guidance['documents'])} items")
    print(f"\nAnswer preview:\n{result['answer'][:400]}...")


if __name__ == "__main__":
    print("\n⚖️  LEGAL GUIDANCE ENGINE — TEST")
    test_static_fallback()
    test_guidance_generation()
    test_full_pipeline_with_guidance()
    print("\n✅ ALL GUIDANCE TESTS COMPLETE")