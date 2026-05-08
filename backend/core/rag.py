"""Phase 3 RAG implementation."""
import os
import json
import numpy as np
import faiss
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from core.text_embedder import TextEmbedder
from utils.logger import logger

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

INDEX_DIR        = os.path.join("data", "index")
FAISS_INDEX_PATH = os.path.join(INDEX_DIR, "faiss.index")
CHUNKS_INDEX_PATH= os.path.join(INDEX_DIR, "chunks_index.json")
CHUNKS_DATA_PATH = os.path.join("data", "processed", "chunks.json")

# ─────────────────────────────────────────────
# EMBEDDING MODEL
# ─────────────────────────────────────────────

EMBED_MODEL_NAME = "hash-384"

# ─────────────────────────────────────────────
# RAG SYSTEM CLASS
# ─────────────────────────────────────────────

class HybridRAG:
    """
    Hybrid Retrieval-Augmented Generation system.
    Combines FAISS (semantic) + BM25 (keyword) + cross-encoder re-ranking.
    """

    def __init__(self):
        self.embedder       = None   # TextEmbedder
        self.faiss_index    = None   # FAISS index
        self.bm25           = None   # BM25 index
        self.chunks         = []     # all chunk dicts
        self.texts          = []     # plain text list (for BM25)
        self.is_ready       = False

    # ─────────────────────────────────────────
    # INITIALISE (load or build)
    # ─────────────────────────────────────────

    def initialise(self, force_rebuild: bool = False):
        """Load existing index or build from scratch."""
        logger.info("Initialising Hybrid RAG system...")

        # Load embedding model
        logger.info(f"Loading embedding model: {EMBED_MODEL_NAME}")
        self.embedder = TextEmbedder()

        os.makedirs(INDEX_DIR, exist_ok=True)

        index_exists = (
            os.path.exists(FAISS_INDEX_PATH) and
            os.path.exists(CHUNKS_INDEX_PATH)
        )

        if index_exists and not force_rebuild:
            logger.info("Found existing index — loading...")
            self._load_index()
        else:
            logger.info("Building index from processed chunks...")
            self._build_index()

        # Always rebuild BM25 (in-memory, fast)
        self._build_bm25()

        self.is_ready = True
        logger.success(
            f"RAG ready — {len(self.chunks)} chunks indexed."
        )

    # ─────────────────────────────────────────
    # BUILD FAISS INDEX
    # ─────────────────────────────────────────

    def _build_index(self):
        """Embed all chunks and build FAISS index."""
        if not os.path.exists(CHUNKS_DATA_PATH):
            raise FileNotFoundError(
                f"Run Phase 1 pipeline first. Missing: {CHUNKS_DATA_PATH}"
            )

        with open(CHUNKS_DATA_PATH, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.texts = [c["text"] for c in self.chunks]

        logger.info(f"Embedding {len(self.texts)} chunks...")
        embeddings = self.embedder.encode(
            self.texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        embeddings = embeddings.astype("float32")

        # Normalise for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build flat index (exact search — suitable for <100k chunks)
        dim = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalise
        self.faiss_index.add(embeddings)

        # Save
        faiss.write_index(self.faiss_index, FAISS_INDEX_PATH)
        with open(CHUNKS_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        logger.info(
            f"FAISS index built — {self.faiss_index.ntotal} vectors, dim={dim}"
        )

    # ─────────────────────────────────────────
    # LOAD FAISS INDEX
    # ─────────────────────────────────────────

    def _load_index(self):
        """Load saved FAISS index and chunks."""
        self.faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        with open(CHUNKS_INDEX_PATH, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        self.texts = [c["text"] for c in self.chunks]
        logger.info(
            f"Loaded FAISS index — {self.faiss_index.ntotal} vectors."
        )

    # ─────────────────────────────────────────
    # BUILD BM25 INDEX
    # ─────────────────────────────────────────

    def _build_bm25(self):
        """Build BM25 keyword index from chunk texts."""
        tokenized = [text.lower().split() for text in self.texts]
        self.bm25 = BM25Okapi(tokenized)
        logger.info("BM25 index built.")

    # ─────────────────────────────────────────
    # SEMANTIC SEARCH (FAISS)
    # ─────────────────────────────────────────

    def _semantic_search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Return (chunk_index, score) pairs via FAISS.
        """
        query_vec = self.embedder.encode(
            [query], convert_to_numpy=True
        ).astype("float32")
        faiss.normalize_L2(query_vec)

        scores, indices = self.faiss_index.search(query_vec, top_k)
        results = [
            (int(idx), float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx != -1
        ]
        return results

    # ─────────────────────────────────────────
    # KEYWORD SEARCH (BM25)
    # ─────────────────────────────────────────

    def _keyword_search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Return (chunk_index, score) pairs via BM25.
        """
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [
            (int(idx), float(scores[idx]))
            for idx in top_indices
            if scores[idx] > 0
        ]
        return results

    # ─────────────────────────────────────────
    # RECIPROCAL RANK FUSION (RRF)
    # ─────────────────────────────────────────

    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Tuple[int, float]],
        keyword_results:  List[Tuple[int, float]],
        k: int = 60,
        semantic_weight: float = 0.6,
        keyword_weight:  float = 0.4
    ) -> List[Tuple[int, float]]:
        """
        Merge semantic + keyword results using weighted RRF.
        RRF score = weight / (k + rank)
        Higher = better.
        """
        rrf_scores: Dict[int, float] = {}

        for rank, (idx, _) in enumerate(semantic_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + \
                               semantic_weight / (k + rank + 1)

        for rank, (idx, _) in enumerate(keyword_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + \
                               keyword_weight / (k + rank + 1)

        # Sort by fused score descending
        sorted_results = sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_results

    # ─────────────────────────────────────────
    # RE-RANKER (cross-encoder style, lightweight)
    # ─────────────────────────────────────────

    def _rerank(
        self,
        query: str,
        candidates: List[Tuple[int, float]],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Re-rank fused candidates by keyword overlap + length bonus.
        (Full cross-encoder re-ranking added in Phase 4 with LLM)
        """
        query_tokens = set(query.lower().split())
        scored = []

        for idx, rrf_score in candidates[:top_n * 3]:  # re-rank wider pool
            chunk = self.chunks[idx]
            text  = chunk["text"].lower()
            tokens = set(text.split())

            # Keyword overlap ratio
            overlap = len(query_tokens & tokens) / (len(query_tokens) + 1e-6)

            # Length bonus: prefer medium-length chunks
            word_count  = len(text.split())
            length_bonus = min(word_count / 150, 1.0)

            # Category boost: exact category match
            category_boost = 0.0
            for q_word in query_tokens:
                if q_word in chunk.get("category", "").lower():
                    category_boost = 0.2
                    break

            final_score = (rrf_score * 0.5) + \
                          (overlap    * 0.3) + \
                          (length_bonus * 0.1) + \
                          (category_boost * 0.1)

            scored.append((idx, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored[:top_n]:
            chunk = self.chunks[idx].copy()
            chunk["relevance_score"] = round(score, 4)
            results.append(chunk)

        return results

    # ─────────────────────────────────────────
    # CONFIDENCE SCORER
    # ─────────────────────────────────────────

    def _compute_confidence(self, results: List[Dict]) -> float:
        """
        Estimate retrieval confidence (0.0 – 1.0).
        Based on top scores and coverage diversity.
        """
        if not results:
            return 0.0

        top_score = results[0].get("relevance_score", 0.0)
        unique_categories = len(set(r.get("category", "") for r in results))
        diversity_bonus   = min(unique_categories / 5, 0.2)

        confidence = min(top_score + diversity_bonus, 1.0)
        return round(confidence, 3)

    # ─────────────────────────────────────────
    # CONTEXT BUILDER
    # ─────────────────────────────────────────

    def _build_context(self, results: List[Dict], max_words: int = 300) -> str:
        """
        Build context string from retrieved chunks.
        Hard cap at max_words to keep prompt size manageable on CPU.
        """
        lines       = ["=== RETRIEVED LEGAL CONTEXT ===\n"]
        total_words = 0

        for i, chunk in enumerate(results, 1):
            text       = chunk["text"]
            chunk_words = len(text.split())

            if total_words + chunk_words > max_words:
            # Add a trimmed version of this chunk if space allows
                remaining = max_words - total_words
                if remaining > 30:
                    text = " ".join(text.split()[:remaining]) + "..."
                    lines.append(
                    f"[Source {i}] {chunk.get('category','')} "
                    f"— {chunk.get('title','')}\n{text}\n"
                    )
                break

            lines.append(
            f"[Source {i}] {chunk.get('category','')} "
            f"— {chunk.get('title','')}\n{text}\n"
            )
            total_words += chunk_words

        return "\n".join(lines)

    # ─────────────────────────────────────────
    # MASTER RETRIEVE
    # ─────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        semantic_k: int = 10,
        keyword_k:  int = 10
    ) -> Dict:
        """
        Full hybrid retrieval pipeline:
        1. Semantic search (FAISS)
        2. Keyword search (BM25)
        3. RRF fusion
        4. Re-ranking
        5. Confidence scoring
        6. Context building

        Returns a RetrievalResult dict.
        """
        if not self.is_ready:
            raise RuntimeError("RAG not initialised. Call .initialise() first.")

        logger.info(f"Retrieving for query: '{query[:80]}...'")

        # Step 1 & 2
        semantic = self._semantic_search(query, semantic_k)
        keyword  = self._keyword_search(query, keyword_k)

        logger.info(
            f"Semantic hits: {len(semantic)} | Keyword hits: {len(keyword)}"
        )

        # Step 3
        fused = self._reciprocal_rank_fusion(semantic, keyword)

        # Step 4
        reranked = self._rerank(query, fused, top_n=top_k)

        # Step 5
        confidence = self._compute_confidence(reranked)

        # Step 6
        context = self._build_context(reranked)

        logger.info(
            f"Retrieved {len(reranked)} chunks | confidence: {confidence}"
        )

        return {
            "query":      query,
            "chunks":     reranked,
            "context":    context,
            "confidence": confidence,
            "num_results": len(reranked)
        }

    # ─────────────────────────────────────────
    # ADD DYNAMIC CHUNKS (uploaded docs)
    # ─────────────────────────────────────────

    def add_chunks_dynamic(self, new_chunks: List[str], metadata: Dict = {}):
        """
        Add chunks from a user-uploaded document to the live index.
        Does NOT persist to disk — session-only.
        """
        if not self.is_ready:
            raise RuntimeError("RAG not initialised.")

        embeddings = self.embedder.encode(
            new_chunks, convert_to_numpy=True
        ).astype("float32")
        faiss.normalize_L2(embeddings)
        self.faiss_index.add(embeddings)

        for i, text in enumerate(new_chunks):
            chunk_dict = {
                "chunk_id":    f"dynamic_{len(self.chunks)+i}",
                "parent_id":   metadata.get("parent_id", "upload"),
                "category":    metadata.get("category", "Uploaded Document"),
                "title":       metadata.get("title", "Uploaded"),
                "text":        text,
                "chunk_index": i,
                "total_chunks": len(new_chunks)
            }
            self.chunks.append(chunk_dict)
            self.texts.append(text)

        # Rebuild BM25 with new texts
        self._build_bm25()

        logger.info(
            f"Added {len(new_chunks)} dynamic chunks. "
            f"Total: {len(self.chunks)}"
        )


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────

rag_system = HybridRAG()
