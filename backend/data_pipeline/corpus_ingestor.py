import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List

REGISTRY_PATH = "data/processed/corpus_registry.json"
CORPUS_ROOT   = "data/corpus"
CHUNKS_PATH   = "data/processed/chunks.json"


# ─────────────────────────────────────────────
# HASHING
# ─────────────────────────────────────────────

def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────

def load_registry() -> Dict:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_registry(registry: Dict):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


# ─────────────────────────────────────────────
# DISCOVER CHANGED FILES
# ─────────────────────────────────────────────

def get_new_or_changed_files(registry: Dict) -> List[str]:
    changed = []

    for path in Path(CORPUS_ROOT).rglob("*.txt"):
        path_str = str(path)
        current_hash = _file_hash(path_str)

        if registry.get(path_str) != current_hash:
            changed.append(path_str)

    return changed


# ─────────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────────

def sliding_window(text: str, size: int = 150, overlap: int = 30):
    words = text.split()
    chunks = []

    step = size - overlap

    for i in range(0, len(words), step):
        chunk = words[i:i+size]
        if len(chunk) >= 15:
            chunks.append(" ".join(chunk))

    return chunks


def chunk_legal_document(text: str, category: str):

    if category == "statute":
        sections = re.split(r'\n(?=Section\s+\d+)', text)
        return [s.strip() for s in sections if len(s.split()) > 15]

    if category == "contract":
        clauses = re.split(r'\n(?=\d+[\.\d]*)', text)
        return [c.strip() for c in clauses if len(c.split()) > 15]

    if category == "judgment":
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        merged = []

        for i in range(0, len(paragraphs), 2):
            merged.append("\n\n".join(paragraphs[i:i+3]))

        return merged

    return sliding_window(text)


# ─────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────

def infer_metadata(filepath: str) -> Dict:
    path = filepath.lower()

    if "statutes" in path:
        category = "statute"
    elif "judgments" in path:
        category = "judgment"
    elif "contracts" in path:
        category = "contract"
    elif "regulations" in path:
        category = "regulation"
    else:
        category = "guide"

    jurisdiction = "general"

    if "india" in path:
        jurisdiction = "india"
    elif "uk" in path:
        jurisdiction = "uk"
    elif "us" in path:
        jurisdiction = "us"

    legal_domain = "general_legal"

    if "tenant" in path:
        legal_domain = "tenant_rights"
    elif "criminal" in path or "ipc" in path:
        legal_domain = "criminal_law"
    elif "employment" in path:
        legal_domain = "employment_law"
    elif "consumer" in path:
        legal_domain = "consumer_rights"

    return {
        "category": category,
        "jurisdiction": jurisdiction,
        "legal_domain": legal_domain,
    }


# ─────────────────────────────────────────────
# INGEST SINGLE FILE
# ─────────────────────────────────────────────

def ingest_single_file(filepath: str):

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    metadata = infer_metadata(filepath)

    category = metadata["category"]

    chunks = chunk_legal_document(text, category)

    parent_id = os.path.splitext(os.path.basename(filepath))[0]

    results = []

    for idx, chunk in enumerate(chunks):

        results.append({
            "chunk_id": f"{parent_id}_chunk_{idx}",
            "parent_id": parent_id,
            "source_file": filepath,
            "category": metadata["category"],
            "jurisdiction": metadata["jurisdiction"],
            "legal_domain": metadata["legal_domain"],
            "title": parent_id.replace("_", " ").title(),
            "text": chunk,
            "chunk_index": idx,
            "total_chunks": len(chunks),
            "word_count": len(chunk.split()),
            "ingested_at": datetime.utcnow().isoformat(),
            "content_hash": _file_hash(filepath)
        })

    return results


# ─────────────────────────────────────────────
# MAIN INGEST
# ─────────────────────────────────────────────

def run_incremental_ingest():

    registry = load_registry()

    new_files = get_new_or_changed_files(registry)

    if not new_files:
        print("No new or changed files.")
        return

    print(f"{len(new_files)} files to ingest.")

    existing_chunks = []

    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            existing_chunks = json.load(f)

    changed_parents = {
        os.path.splitext(os.path.basename(f))[0]
        for f in new_files
    }

    surviving_chunks = [
        c for c in existing_chunks
        if c.get("parent_id") not in changed_parents
    ]

    new_chunks = []

    for filepath in new_files:

        chunks = ingest_single_file(filepath)

        new_chunks.extend(chunks)

        registry[filepath] = _file_hash(filepath)

    all_chunks = surviving_chunks + new_chunks

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    save_registry(registry)

    print(f"Done. Total chunks: {len(all_chunks)}")


if __name__ == "__main__":
    run_incremental_ingest()