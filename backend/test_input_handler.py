import sys
sys.path.insert(0, ".")
from core.input_handler import process_input

# Test 1: plain text
r = process_input(text="What is a breach of contract?")
print(f"Type: {r['input_type']} | Words: {len(r['content'].split())}")

# Test 2: chat
r = process_input(
    text="Can I sue my landlord?",
    chat_history=[{"role": "user", "content": "My landlord won't fix the heat."}]
)
print(f"Type: {r['input_type']} | Words: {len(r['content'].split())}")

# Test 3: raw document
long_text = "This agreement is made between " + ("the parties " * 120)
r = process_input(text=long_text)
print(f"Type: {r['input_type']} | Chunks: {len(r['chunks'])}")

# Test 4: comparison
r = process_input(text="Contract version A text here.", doc_b="Contract version B text here.")
print(f"Type: {r['input_type']}")