from typing import Dict, Any, List, Optional
import numpy as np
import hashlib

def _hash_embed(text: str, dim: int = 256) -> np.ndarray:
    # Deterministic lightweight “embedding” for baseline OSS demo
    h = hashlib.sha256(text.encode("utf-8")).digest()
    rng = np.random.default_rng(int.from_bytes(h[:8], "little"))
    v = rng.normal(size=(dim,))
    v = v / (np.linalg.norm(v) + 1e-9)
    return v.astype(np.float32)

class InMemoryDocIndex:
    def __init__(self, dim: int = 256):
        self.dim = dim
        self._items: List[Dict[str, Any]] = []

    def ingest(self, docs: List[Dict[str, Any]]) -> None:
        for d in docs:
            emb = _hash_embed(d["text"], dim=self.dim)
            self._items.append({**d, "emb": emb})

    def search(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        q = _hash_embed(query, dim=self.dim)
        items = self._items
        if filters:
            for key, val in filters.items():
                items = [it for it in items if it.get(key) == val]
        if not items:
            return []
        sims = [(float(np.dot(q, it["emb"])), it) for it in items]
        sims.sort(key=lambda x: x[0], reverse=True)
        hits = []
        for score, it in sims[:k]:
            hits.append({
                "score": score,
                "title": it.get("title",""),
                "url": it.get("url",""),
                "source": it.get("source",""),
                "text": it.get("text",""),
            })
        return hits
