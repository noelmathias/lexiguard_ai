import json
import os
from typing import List, Dict
from utils.logger import logger

RAW_DATA_PATH = os.path.join("data", "raw", "legal_seed.json")

def load_seed_data() -> List[Dict]:
    """Load seed legal documents from JSON file."""
    if not os.path.exists(RAW_DATA_PATH):
        logger.error(f"Seed data not found at: {RAW_DATA_PATH}")
        raise FileNotFoundError(f"Missing: {RAW_DATA_PATH}")

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} documents from seed data.")
    return data

def load_custom_documents(folder: str = "data/raw") -> List[Dict]:
    """
    Load any additional .txt files from the raw folder.
    Treats each file as one document.
    """
    custom_docs = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            doc_id = filename.replace(".txt", "")
            custom_docs.append({
                "id": doc_id,
                "category": "Custom",
                "title": filename,
                "text": content
            })
            logger.info(f"Loaded custom document: {filename}")
    return custom_docs