import sys
sys.path.insert(0, ".")

from core.docgen import (
    generate_document_static,
    generate_legal_document,
    extract_document_fields,
    DOCUMENT_TYPES
)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


SITUATION_NOTICE = (
    "My landlord Robert Brown at 456 Park Avenue, Chicago refused to "
    "return my security deposit of $3000 after I vacated the flat at "
    "123 Oak Street on 15 January 2025. I have all payment receipts "
    "and move-out inspection report showing no damage."
)

SITUATION_COMPLAINT = (
    "I purchased a laptop from TechMart Store, 789 Mall Road on "
    "1 December 2024 for $1200. It stopped working within 10 days. "
    "The store is refusing to replace or refund despite warranty. "
    "I have the receipt and warranty card."
)

SITUATION_FIR = (
    "On 20 January 2025 at around 8pm, a person named Raj Kumar who "
    "lives at 55 River Road came to my house and assaulted me causing "
    "injuries to my arm. Two neighbours witnessed this. "
    "I have medical reports and photos of injuries."
)


def test_document_types():
    separator("TEST 1 — DOCUMENT TYPE REGISTRY")

    for k, v in DOCUMENT_TYPES.items():
        print(f"  {k:20} → {v['label']}")
        assert "label"       in v
        assert "description" in v
        assert "use_cases"   in v

    print("\n✅ Document type registry OK.")


def test_static_generation():
    separator("TEST 2 — STATIC TEMPLATE GENERATION (no LLM)")

    for doc_type, situation in [
        ("legal_notice",    SITUATION_NOTICE),
        ("complaint_letter", SITUATION_COMPLAINT),
        ("fir_draft",        SITUATION_FIR)
    ]:
        result = generate_legal_document(
            doc_type  = doc_type,
            situation = situation,
            use_llm   = False
        )

        print(f"\n  [{result['doc_label']}]")
        print(f"  Words     : {result['word_count']}")
        print(f"  Mode      : {result['generation_mode']}")
        print(f"  Preview   :\n")
        # Print first 8 lines
        lines = result["document"].split("\n")
        for line in lines[:8]:
            print(f"    {line}")
        print(f"    ...")

        assert result["word_count"]      > 50,     "Document too short"
        assert result["generation_mode"] == "static"
        assert "[NOT PROVIDED]" in result["document"] or \
               result["word_count"] > 80

    print("\n✅ Static generation passed.")


def test_field_extraction():
    separator("TEST 3 — FIELD EXTRACTION (1 LLM call)")

    print("  Extracting fields from situation description...")

    fields = extract_document_fields(SITUATION_NOTICE, "legal_notice")

    print(f"\n  Extracted fields:")
    for k, v in fields.items():
        if v:
            print(f"    {k:25}: {str(v)[:60]}")

    assert isinstance(fields, dict), "Fields must be a dict"
    assert len(fields) > 0,         "No fields extracted"
    print("\n✅ Field extraction passed.")


def test_llm_generation():
    separator("TEST 4 — LLM DOCUMENT GENERATION (2 LLM calls)")

    for doc_type, situation, label in [
        ("legal_notice",     SITUATION_NOTICE,    "Legal Notice"),
        ("complaint_letter", SITUATION_COMPLAINT, "Complaint Letter"),
        ("fir_draft",        SITUATION_FIR,       "FIR Draft")
    ]:
        print(f"\n  Generating {label}...")

        result = generate_legal_document(
            doc_type  = doc_type,
            situation = situation,
            use_llm   = True
        )

        print(f"  Words     : {result['word_count']}")
        print(f"  Mode      : {result['generation_mode']}")
        print(f"\n  Document preview:")
        lines = result["document"].split("\n")
        for line in lines[:10]:
            print(f"    {line}")
        print(f"    ...")

        assert result["word_count"]      > 80
        assert result["generation_mode"] == "llm"

    print("\n✅ LLM generation passed.")


def test_with_user_info():
    separator("TEST 5 — GENERATION WITH PRE-FILLED USER INFO")

    user_info = {
        "sender_name":       "Alice Johnson",
        "sender_address":    "22 Elm Street, New York, NY 10001",
        "recipient_name":    "Bob Williams",
        "recipient_address": "99 Oak Avenue, New York, NY 10002",
        "subject":           "Unlawful withholding of security deposit",
        "facts": (
            "I vacated the property at 99 Oak Avenue on 31 Dec 2024 "
            "after giving 30 days notice. The deposit of $2500 has not "
            "been returned despite 21 days having passed."
        ),
        "legal_basis":       "landlord-tenant law and rental agreement",
        "demand":            "return the full security deposit of $2500",
        "deadline":          "15"
    }

    result = generate_legal_document(
        doc_type  = "legal_notice",
        situation = "Deposit dispute",
        user_info = user_info,
        use_llm   = True
    )

    print(f"  Words  : {result['word_count']}")
    print(f"  Mode   : {result['generation_mode']}")
    print(f"\n  Document:\n")
    for line in result["document"].split("\n")[:15]:
        print(f"    {line}")

    assert "Alice Johnson"  in result["document"] or \
           result["word_count"] > 80
    print("\n✅ Pre-filled user_info generation passed.")


if __name__ == "__main__":
    print("\n⚖️  DOCUMENT GENERATION — TEST")

    test_document_types()
    test_static_generation()

    run_llm = input(
        "\nRun LLM tests? Uses up to 2 Ollama calls per doc. (y/n): "
    ).strip().lower()

    if run_llm == "y":
        test_field_extraction()
        test_llm_generation()
        test_with_user_info()
    else:
        print("Skipping LLM tests.")

    print("\n✅ ALL DOCGEN TESTS COMPLETE")