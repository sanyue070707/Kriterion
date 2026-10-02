"""In-memory BM25 retrieval — a self-contained Okapi BM25 implementation.

Depends on nothing beyond the standard library; parameters follow the standard
k1 / b formulation.
"""

from __future__ import annotations

import math
import re
from typing import Any

_TOKEN_RE = re.compile(r"\w+")

K1 = 1.5
B = 0.75


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return _TOKEN_RE.findall(text.lower())


class BM25Store:
    """In-memory Okapi BM25 store for a single document collection."""

    def __init__(self) -> None:
        self._corpus: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_freq: dict[str, int] = {}
        self._avgdl: float = 0.0

    def index(self, documents: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:
        """Index documents for BM25 retrieval."""
        self._corpus = documents
        self._metadatas = metadatas or [{} for _ in documents]
        self._doc_tokens = [_tokenize(doc) for doc in documents]

        self._doc_freq = {}
        for tokens in self._doc_tokens:
            for token in set(tokens):
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

        total = sum(len(t) for t in self._doc_tokens)
        self._avgdl = total / len(self._doc_tokens) if self._doc_tokens else 0.0

    def _idf(self, term: str) -> float:
        n = len(self._corpus)
        df = self._doc_freq.get(term, 0)
        # BM25 idf with +0.5 smoothing, floored at a small positive value.
        return max(0.0, math.log(1 + (n - df + 0.5) / (df + 0.5)))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search documents using BM25."""
        if not self._corpus:
            return []

        query_terms = _tokenize(query)
        scores: list[tuple[int, float]] = []
        for idx, tokens in enumerate(self._doc_tokens):
            dl = len(tokens)
            score = 0.0
            for term in query_terms:
                tf = tokens.count(term)
                if tf == 0:
                    continue
                denom = tf + K1 * (1 - B + B * dl / self._avgdl) if self._avgdl else tf + K1
                score += self._idf(term) * tf * (K1 + 1) / denom
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "text": self._corpus[i],
                "score": float(s),
                "metadata": self._metadatas[i] if i < len(self._metadatas) else {},
            }
            for i, s in scores[:top_k]
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
