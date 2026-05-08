import json
import os
import sys
from typing import List, Dict
from tqdm import tqdm

# Ensure package imports work when running the script directly from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.collector import load_seed_data, load_custom_documents
from data_pipeline.cleaner import clean_text
from data_pipeline.chunker import chunk_document
from utils.logger import logger

PROCESSED_DIR = os.path.join("data", "processed")
CHUNKS_PATH = os.path.join(PROCESSED_DIR, "chunks.json")
METADATA_PATH = os.path.join(PROCESSED_DIR, "metadata.json")

def run_pipeline() -> List[Dict]:
    """
    Full preprocessing pipeline:
    1. Load seed + custom documents
    2. Clean text
    3. Chunk documents
    4. Save chunks and metadata
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Step 1: Collect
    logger.info("=== STEP 1: Loading documents ===")
    documents = load_seed_data()
    custom = load_custom_documents()
    documents.extend(custom)
    logger.info(f"Total documents loaded: {len(documents)}")

    # Step 2: Clean
    logger.info("=== STEP 2: Cleaning text ===")
    for doc in documents:
        doc['text'] = clean_text(doc['text'])

    # Step 3: Chunk
    logger.info("=== STEP 3: Chunking documents ===")
    all_chunks = []
    metadata = []

    for doc in tqdm(documents, desc="Chunking"):
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
        metadata.append({
            "id": doc['id'],
            "category": doc.get('category'),
            "title": doc.get('title'),
            "num_chunks": len(chunks)
        })

    logger.info(f"Total chunks created: {len(all_chunks)}")

    # Step 4: Save
    logger.info("=== STEP 4: Saving processed data ===")
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Chunks saved to: {CHUNKS_PATH}")
    logger.info(f"Metadata saved to: {METADATA_PATH}")
    logger.success("=== PIPELINE COMPLETE ===")

    return all_chunks

if __name__ == "__main__":
    chunks = run_pipeline()
    print(f"\n✅ Done. Total chunks: {len(chunks)}")
    print(f"📄 Sample chunk:\n{json.dumps(chunks[0], indent=2)}")