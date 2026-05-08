import sys
sys.path.insert(0, ".")

from core.rag import rag_system
from core.agents import run_agent_pipeline, safe_parse_json
from core.guidance import (
    process_guidance_from_pipeline,
    format_guidance_for_response
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_safe_parser():
    separator("TEST 0 — SAFE JSON PARSER")

    assert safe_parse_json('{"a":1}', {}) == {"a": 1}
    print("✅ Direct parse OK")

    assert safe_parse_json('```json\n{"a":1}\n```', {}).get("a") == 1
    print("✅ Fence strip OK")

    r = safe_parse_json('{"a": 1, "b": "hello"', {"fallback": True})
    print(f"✅ Truncation recovery: {r}")

    assert safe_parse_json("", {"x": 1}) == {"x": 1}
    print("✅ Empty fallback OK")


def test_full_pipeline():
    separator("TEST 1 — FULL UNIFIED PIPELINE (1 LLM call)")

    rag_system.initialise()

    queries = [
        "My landlord locked me out without notice.",
        "My employer fired me after I filed a workers compensation claim.",
        "How do I file an FIR against my neighbour?"
    ]

    for query in queries:
        print(f"\n--- Query: {query} ---")

        retrieval = rag_system.retrieve(query, top_k=3)
        result    = run_agent_pipeline(
            query=query,
            context=retrieval["context"],
            confidence=retrieval["confidence"],
            chunks=retrieval["chunks"]
        )

        guidance = format_guidance_for_response(
            process_guidance_from_pipeline(
                guidance_raw=result["guidance_raw"],
                intent=result["intent"]
            )
        )

        print(f"  Intent    : {result['intent']}")
        print(f"  Rewritten : {result['rewritten_query']}")
        print(f"  Urgency   : {guidance['urgency_display']}")
        print(f"  Domain    : {guidance['legal_domain']}")
        print(f"  Rights    : {len(guidance['rights'])} | "
              f"Steps: {len(guidance['steps'])} | "
              f"Docs: {len(guidance['documents'])}")
        print(f"  Answer preview: {result['answer'][:200]}...")


if __name__ == "__main__":
    print("\n⚖️  PIPELINE TEST — 1 LLM call per query")
    test_safe_parser()
    test_full_pipeline()
    print("\n✅ ALL TESTS COMPLETE")