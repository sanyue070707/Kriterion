"""In-memory BM25 sparse retrieval using rank-bm25."""

from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"\w+", text.lower())


class BM25Store:
    """In-memory BM25 store for a single document collection."""

    def __init__(self) -> None:
        self._corpus: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None

    def index(self, documents: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:
        """Index documents for BM25 retrieval."""
        self._corpus = documents
        self._metadatas = metadatas or [{} for _ in documents]
        tokenized = [_tokenize(doc) for doc in documents]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search documents using BM25."""
        if self._bm25 is None or not self._corpus:
            return []
        tokenized_query = _tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {
                "text": self._corpus[i],
                "score": float(scores[i]),
                "metadata": self._metadatas[i] if i < len(self._metadatas) else {},
            }
            for i in top_indices
            if scores[i] > 0
        ]

    @property
    def size(self) -> int:
        return len(self._corpus)


# Global BM25 stores (one per collection)
_bm25_stores: dict[str, BM25Store] = {}


def get_bm25_store(collection_name: str) -> BM25Store:
    """Get or create a BM25 store for a collection."""
    if collection_name not in _bm25_stores:
        _bm25_stores[collection_name] = BM25Store()
    return _bm25_stores[collection_name]
