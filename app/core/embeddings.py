import hashlib
from typing import List, Protocol

import numpy as np


class Embedder(Protocol):
    def embed_text(self, text: str) -> np.ndarray:
        ...

    def embed_many(self, texts: List[str]) -> List[np.ndarray]:
        ...


class HashEmbedder:
    def __init__(self, dim: int = 256):
        self.dim = dim

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        vector = rng.normal(size=(self.dim,))
        return self._normalize(vector)

    def embed_many(self, texts: List[str]) -> List[np.ndarray]:
        return [self.embed_text(text) for text in texts]


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("sentence-transformers is not installed") from exc

        self.model = SentenceTransformer(model_name)

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        vector = self.model.encode([text], convert_to_numpy=True)[0]
        return self._normalize(vector)

    def embed_many(self, texts: List[str]) -> List[np.ndarray]:
        vectors = self.model.encode(texts, convert_to_numpy=True)
        return [self._normalize(vector) for vector in vectors]
