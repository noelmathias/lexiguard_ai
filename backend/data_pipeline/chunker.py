from typing import List, Dict
import re

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_text(
    text: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> List[str]:
    """
    Split text into overlapping word-level chunks.
    chunk_size: max words per chunk
    overlap: words shared between consecutive chunks
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks

def chunk_document(doc: Dict, chunk_size: int = 150, overlap: int = 30) -> List[Dict]:
    """
    Chunk a single document dict and return list of chunk dicts.
    Each chunk inherits the parent document's metadata.
    """
    chunks = chunk_text(doc['text'], chunk_size, overlap)
    result = []
    for i, chunk in enumerate(chunks):
        result.append({
            "chunk_id": f"{doc['id']}_chunk_{i}",
            "parent_id": doc['id'],
            "category": doc.get('category', 'General'),
            "title": doc.get('title', ''),
            "text": chunk,
            "chunk_index": i,
            "total_chunks": len(chunks)
        })
    return result