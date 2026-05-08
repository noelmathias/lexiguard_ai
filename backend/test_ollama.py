import sys
sys.path.insert(0, ".")

from core.llm_provider import (
    check_ollama_health,
    call_llm,
    call_llm_for_json,
    safe_parse_json
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_health():
    separator("TEST 1 — OLLAMA HEALTH CHECK")
    health = check_ollama_health()
    print(f"  Ollama running  : {health['ollama_running']}")
    print(f"  Model           : {health['model']}")
    print(f"  Model available : {health['model_available']}")
    print(f"  Status          : {health['status']}")
    print(f"  All models      : {health['available_models']}")

    if not health["ollama_running"]:
        print("\n  ❌ Ollama is not running. Start it with: ollama serve")
        return False
    if not health["model_available"]:
        print(f"\n  ❌ Model not found. Pull it with: ollama pull {health['model']}")
        return False

    print("\n  ✅ Ollama is ready.")
    return True


def test_plain_call():
    separator("TEST 2 — PLAIN TEXT CALL")
    response = call_llm(
        prompt     = "In one sentence, what is a contract?",
        max_tokens = 100,
        expect_json= False
    )
    print(f"  Response: {response}")
    assert len(response) > 10, "Response too short"
    print("  ✅ Plain call passed.")


def test_json_call():
    separator("TEST 3 — JSON CALL")
    prompt = """Classify this legal query.

Query: "My landlord locked me out without notice."

Return ONLY this JSON:
{
  "intent": "<tenant_rights|employment_law|criminal_law|general_legal>",
  "confidence": <0.0-1.0>,
  "urgency": "<low|medium|high>"
}"""

    result = call_llm_for_json(
        prompt   = prompt,
        fallback = {"intent": "general_legal", "confidence": 0.5, "urgency": "medium"}
    )

    print(f"  Intent    : {result.get('intent')}")
    print(f"  Confidence: {result.get('confidence')}")
    print(f"  Urgency   : {result.get('urgency')}")

    assert "intent" in result, "Missing intent key"
    print("  ✅ JSON call passed.")


def test_full_pipeline():
    separator("TEST 4 — FULL PIPELINE")

    from core.rag import rag_system
    from core.agents import run_agent_pipeline

    rag_system.initialise()
    query     = "My landlord is refusing to return my deposit after I moved out."
    retrieval = rag_system.retrieve(query, top_k=3)

    print(f"  RAG confidence: {retrieval['confidence']}")
    print(f"  Chunks found  : {retrieval['num_results']}")
    print(f"  Calling Ollama pipeline...")

    result = run_agent_pipeline(
        query     = query,
        context   = retrieval["context"],
        confidence= retrieval["confidence"],
        chunks    = retrieval["chunks"]
    )

    print(f"\n  Intent   : {result['intent']}")
    print(f"  Rewritten: {result['rewritten_query']}")
    print(f"  Urgency  : {result['guidance_raw'].get('urgency')}")
    print(f"\n  Answer preview:")
    print(f"  {result['answer'][:300]}...")

    assert result["intent"] != "", "Empty intent"
    print("\n  ✅ Full pipeline passed.")


if __name__ == "__main__":
    print("\n⚙️  OLLAMA PROVIDER TEST")

    ok = test_health()
    if not ok:
        print("\n❌ Fix Ollama setup before running further tests.")
        sys.exit(1)

    test_plain_call()
    test_json_call()
    test_full_pipeline()

    print("\n✅ ALL OLLAMA TESTS COMPLETE")