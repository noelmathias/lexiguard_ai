"""Lightweight deterministic text embedder used for container-safe builds."""
import hashlib
import re
from typing import Iterable, List

import numpy as np


TOKEN_RE = re.compile(r"\b[a-z0-9_]+\b")


class TextEmbedder:
    """Hash tokens into a fixed-width dense vector for FAISS search."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _encode_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        tokens = TOKEN_RE.findall((text or "").lower())

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            vector[bucket] += sign * weight

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        return vector

    def encode(
        self,
        texts: Iterable[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True
    ) -> np.ndarray:
        del batch_size, show_progress_bar, convert_to_numpy
        rows: List[np.ndarray] = [self._encode_one(text) for text in texts]
        if not rows:
            return np.empty((0, self.dim), dtype=np.float32)
        return np.vstack(rows).astype("float32")
