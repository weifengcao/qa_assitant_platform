from typing import Dict, Any, List, Optional
import numpy as np
import hashlib
import re

_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))

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
            self._items.append({**d, "emb": emb, "tokens": _tokenize(d.get("text", ""))})

    def search(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        q = _hash_embed(query, dim=self.dim)
        q_tokens = _tokenize(query)
        items = self._items
        if filters:
            for key, val in filters.items():
                items = [it for it in items if it.get(key) == val]
        if not items:
            return []
        sims = []
        for it in items:
            vec_score = float(np.dot(q, it["emb"]))
            lex_score = 0.0
            if q_tokens:
                overlap = len(q_tokens.intersection(it.get("tokens", set())))
                lex_score = overlap / max(len(q_tokens), 1)
            score = (0.75 * vec_score) + (0.25 * lex_score)
            sims.append((score, vec_score, lex_score, it))
        sims.sort(key=lambda x: x[0], reverse=True)
        hits = []
        for score, vec_score, lex_score, it in sims[:k]:
            hits.append({
                "score": score,
                "vector_score": vec_score,
                "lexical_score": lex_score,
                "title": it.get("title",""),
                "url": it.get("url",""),
                "source": it.get("source",""),
                "text": it.get("text",""),
            })
        return hits
