"""Workspace indexing helpers."""
"""
Per-workspace document index.
Separate from the global corpus index.
Merged at retrieval time, not at index time.
"""
import os
import json
import faiss
import numpy as np
from typing import Callable, Dict, List
from core.text_embedder import TextEmbedder
from utils.logger import logger


class WorkspaceIndex:
    """
    Lightweight FAISS index for a single workspace's uploaded documents.
    Lives in memory only — rebuilt from stored chunks on demand.
    One instance per active workspace.
    """

    def __init__(self, workspace_id: str, embedder: TextEmbedder):
        self.workspace_id = workspace_id
        self.embedder     = embedder
        self.chunks:      List[Dict] = []
        self.faiss_index  = None
        self._chunks_dir  = f"data/workspace_chunks/{workspace_id}"
        os.makedirs(self._chunks_dir, exist_ok=True)

    def add_document(self, chunks: List[Dict], doc_id: str):
        """Index chunks from one uploaded document."""
        if not chunks:
            return

        texts      = [c["text"] for c in chunks]
        embeddings = self.embedder.encode(
            texts, convert_to_numpy=True, batch_size=16
        ).astype("float32")
        faiss.normalize_L2(embeddings)

        # Initialise or extend index
        dim = embeddings.shape[1]
        if self.faiss_index is None:
            self.faiss_index = faiss.IndexFlatIP(dim)

        start_idx = len(self.chunks)
        self.faiss_index.add(embeddings)
        self.chunks.extend(chunks)

        # Persist chunks to disk so they survive server restart
        chunk_path = os.path.join(self._chunks_dir, f"{doc_id}.json")
        with open(chunk_path, "w") as f:
            json.dump(chunks, f)

        logger.info(
            f"[WS Index] Added {len(chunks)} chunks for doc {doc_id} "
            f"in workspace {self.workspace_id}"
        )

    def load_from_disk(self):
        """Rebuild index from persisted chunk files."""
        all_chunks = []
        for fname in os.listdir(self._chunks_dir):
            if fname.endswith(".json"):
                with open(os.path.join(self._chunks_dir, fname)) as f:
                    all_chunks.extend(json.load(f))

        if not all_chunks:
            return

        texts      = [c["text"] for c in all_chunks]
        embeddings = self.embedder.encode(
            texts, convert_to_numpy=True, batch_size=16
        ).astype("float32")
        faiss.normalize_L2(embeddings)

        dim              = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dim)
        self.faiss_index.add(embeddings)
        self.chunks      = all_chunks

        logger.info(
            f"[WS Index] Loaded {len(all_chunks)} chunks "
            f"for workspace {self.workspace_id}"
        )

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Semantic search within workspace documents only."""
        if self.faiss_index is None or len(self.chunks) == 0:
            return []

        query_vec = self.embedder.encode(
            [query], convert_to_numpy=True
        ).astype("float32")
        faiss.normalize_L2(query_vec)

        k        = min(top_k, len(self.chunks))
        scores, indices = self.faiss_index.search(query_vec, k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0:
                chunk = self.chunks[int(idx)].copy()
                chunk["relevance_score"] = float(score)
                chunk["source"]          = "workspace"
                results.append(chunk)

        return results


class WorkspaceIndexCache:
    """
    Simple in-memory cache of WorkspaceIndex instances.
    Prevents rebuilding the index on every request.
    """
    def __init__(self, embedder_getter: Callable[[], TextEmbedder]):
        self._embedder_getter = embedder_getter
        self._cache: Dict[str, WorkspaceIndex] = {}

    def get(self, workspace_id: str) -> WorkspaceIndex:
        if workspace_id not in self._cache:
            idx = WorkspaceIndex(workspace_id, self._embedder_getter())
            idx.load_from_disk()
            self._cache[workspace_id] = idx
        return self._cache[workspace_id]

    def invalidate(self, workspace_id: str):
        """Call after adding a new document to force index rebuild."""
        self._cache.pop(workspace_id, None)
