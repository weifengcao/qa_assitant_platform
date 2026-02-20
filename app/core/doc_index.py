import re
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np

from app.core.embeddings import Embedder, HashEmbedder

_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


@runtime_checkable
class DocIndex(Protocol):
    def ingest(self, chunks: List[Dict[str, Any]]) -> None:
        ...

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        ...

    def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        ...


class _BaseInMemoryDocIndex:
    def __init__(self, embedder: Optional[Embedder] = None):
        self.embedder = embedder or HashEmbedder()
        self._items: List[Dict[str, Any]] = []

    @staticmethod
    def _match_filters(item: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True
        return all(item.get(key) == value for key, value in filters.items())

    def ingest(self, chunks: List[Dict[str, Any]]) -> None:
        for chunk in chunks:
            text = chunk.get("text", "")
            vector = self.embedder.embed_text(text)
            self._items.append(
                {
                    **chunk,
                    "emb": vector,
                    "tokens": _tokenize(text),
                }
            )

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        return sum(1 for item in self._items if self._match_filters(item, filters))

    def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        if not filters:
            removed = len(self._items)
            self._items = []
            return removed

        kept: List[Dict[str, Any]] = []
        removed = 0
        for item in self._items:
            if self._match_filters(item, filters):
                removed += 1
            else:
                kept.append(item)
        self._items = kept
        return removed

    def _query_items(self, query: str, filters: Optional[Dict[str, Any]]) -> tuple[np.ndarray, set[str], List[Dict[str, Any]]]:
        query_vector = self.embedder.embed_text(query)
        query_tokens = _tokenize(query)
        items = [item for item in self._items if self._match_filters(item, filters)]
        return query_vector, query_tokens, items

    @staticmethod
    def _lexical_score(query_tokens: set[str], item_tokens: set[str]) -> float:
        if not query_tokens:
            return 0.0
        overlap = len(query_tokens.intersection(item_tokens))
        return overlap / max(len(query_tokens), 1)

    @staticmethod
    def _to_hit(
        item: Dict[str, Any],
        score: float,
        vector_score: float,
        lexical_score: float,
    ) -> Dict[str, Any]:
        return {
            "score": score,
            "vector_score": vector_score,
            "lexical_score": lexical_score,
            "bm25_score": lexical_score,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "section_heading": item.get("section_heading"),
            "updated_at": item.get("updated_at"),
            "text": item.get("text", ""),
        }


class InMemoryDocIndex(_BaseInMemoryDocIndex):
    # Vector-only in-memory index.
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if k is not None:
            top_k = k
        query_vector, _, items = self._query_items(query, filters)
        if not items:
            return []

        scored = []
        for item in items:
            vector_score = float(np.dot(query_vector, item["emb"]))
            score = vector_score
            scored.append((score, vector_score, 0.0, item))

        scored.sort(key=lambda row: row[0], reverse=True)
        return [
            self._to_hit(item=item, score=score, vector_score=vector_score, lexical_score=lexical_score)
            for score, vector_score, lexical_score, item in scored[:top_k]
        ]


class HybridDocIndex(_BaseInMemoryDocIndex):
    # Hybrid index that combines lexical overlap and vector similarity.
    def __init__(self, alpha: float = 0.75, embedder: Optional[Embedder] = None):
        super().__init__(embedder=embedder)
        self.alpha = max(0.0, min(1.0, alpha))

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if k is not None:
            top_k = k
        query_vector, query_tokens, items = self._query_items(query, filters)
        if not items:
            return []

        scored = []
        for item in items:
            vector_score = float(np.dot(query_vector, item["emb"]))
            lexical_score = self._lexical_score(query_tokens, item.get("tokens", set()))
            score = (self.alpha * vector_score) + ((1.0 - self.alpha) * lexical_score)
            scored.append((score, vector_score, lexical_score, item))

        scored.sort(key=lambda row: row[0], reverse=True)
        return [
            self._to_hit(item=item, score=score, vector_score=vector_score, lexical_score=lexical_score)
            for score, vector_score, lexical_score, item in scored[:top_k]
        ]
