import sys
sys.path.insert(0, ".")

from core.rag import rag_system

def test_rag():
    print("\n" + "="*60)
    print("  HYBRID RAG SYSTEM — TEST")
    print("="*60)

    # Initialise (builds index on first run)
    rag_system.initialise()

    queries = [
        "What are my rights as a tenant if landlord refuses repairs?",
        "How do I file an FIR?",
        "What makes a contract legally enforceable?",
        "Can my employer enforce a non-compete agreement?",
        "What is a penalty clause in a contract?"
    ]

    for query in queries:
        print(f"\n{'─'*60}")
        print(f"QUERY: {query}")
        result = rag_system.retrieve(query, top_k=3)

        print(f"Confidence : {result['confidence']}")
        print(f"Chunks found: {result['num_results']}")
        for i, chunk in enumerate(result["chunks"], 1):
            print(f"\n  [{i}] {chunk['category']} — {chunk['title']}")
            print(f"       Score : {chunk['relevance_score']}")
            print(f"       Preview: {chunk['text'][:120]}...")

    print("\n" + "="*60)
    print("✅ RAG TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_rag()