import sys
sys.path.insert(0, ".")

from core.docgen import (
    clean_document_text,
    extract_placeholders,
    format_document_response,
    build_structured_fallback,
    generate_legal_document,
    DOCUMENT_TITLE_MAP
)


def separator(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


def test_cleaner():
    separator("TEST 1 — TEXT CLEANER")

    raw = "Line one\\n\\nLine two   \n\n\n\nLine three   "
    cleaned = clean_document_text(raw)

    assert "\\n" not in cleaned,          "Escaped newlines not converted"
    assert "   " not in cleaned,          "Trailing spaces not stripped"
    lines = cleaned.split("\n")
    blank_runs = 0
    max_run    = 0
    for line in lines:
        if line == "":
            blank_runs += 1
            max_run = max(max_run, blank_runs)
        else:
            blank_runs = 0
    assert max_run <= 2, "More than 2 consecutive blank lines remain"
    print(f"  Cleaned output:\n  {repr(cleaned[:80])}")
    print("  ✅ Cleaner passed.")


def test_placeholder_extractor():
    separator("TEST 2 — PLACEHOLDER EXTRACTOR")

    text = (
        "Dear [RECIPIENT NAME],\n"
        "I, [SENDER NAME], at [SENDER ADDRESS] hereby...\n"
        "Amount: [AMOUNT]\n"
        "Contact [RECIPIENT NAME] again.\n"   # duplicate
        "[NOT PROVIDED]"
    )

    placeholders = extract_placeholders(text)
    print(f"  Found: {placeholders}")

    assert "RECIPIENT NAME" in placeholders
    assert "SENDER NAME"    in placeholders
    assert "AMOUNT"         in placeholders
    assert "NOT PROVIDED"   in placeholders
    # Duplicates removed
    assert placeholders.count("RECIPIENT NAME") == 1
    print("  ✅ Extractor passed.")


def test_title_mapping():
    separator("TEST 3 — TITLE MAPPING")

    for doc_type, expected_title in [
        ("legal_notice",     "Legal Notice"),
        ("complaint_letter", "Formal Complaint Letter"),
        ("fir_draft",        "First Information Report (FIR)")
    ]:
        title = DOCUMENT_TITLE_MAP.get(doc_type, "")
        print(f"  {doc_type:20} → {title}")
        assert title == expected_title, f"Wrong title for {doc_type}"

    print("  ✅ Title mapping passed.")


def test_format_response():
    separator("TEST 4 — FORMAT DOCUMENT RESPONSE")

    raw = generate_legal_document(
        doc_type  = "legal_notice",
        situation = "Landlord refusing to return $2000 deposit.",
        use_llm   = False
    )
    result = format_document_response(raw, "legal_notice")

    print(f"  Keys       : {list(result.keys())}")
    print(f"  Doc keys   : {list(result['document'].keys())}")
    print(f"  Title      : {result['document']['title']}")
    print(f"  Placeholders: {result['document']['placeholders'][:5]}")
    print(f"  Word count : {result['word_count']}")

    assert result["document"]["type"]         == "legal_notice"
    assert result["document"]["title"]        == "Legal Notice"
    assert isinstance(result["document"]["placeholders"], list)
    assert isinstance(result["document"]["content"], str)
    assert len(result["document"]["content"]) > 50
    print("  ✅ Format response passed.")


def test_structured_fallback():
    separator("TEST 5 — STRUCTURED FALLBACK")

    for doc_type in ["legal_notice", "complaint_letter", "fir_draft"]:
        fb = build_structured_fallback(doc_type)
        assert fb["status"]                      == "fallback"
        assert fb["document"]["type"]            == doc_type
        assert isinstance(fb["document"]["content"], str)
        assert isinstance(fb["document"]["placeholders"], list)
        assert len(fb["document"]["placeholders"]) > 0
        print(f"  ✅ {doc_type:20} fallback — "
              f"{len(fb['document']['placeholders'])} placeholders")

    print("  ✅ Fallback passed.")


if __name__ == "__main__":
    print("\n⚖️  DOCUMENT FORMATTING LAYER — TEST")
    test_cleaner()
    test_placeholder_extractor()
    test_title_mapping()
    test_format_response()
    test_structured_fallback()
    print("\n✅ ALL FORMATTING TESTS COMPLETE")