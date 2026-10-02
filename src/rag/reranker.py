"""BGE-reranker-v2-m3 wrapper.

Supports two modes:
- "local": Uses sentence-transformers CrossEncoder
- "mock": Returns simple cosine-similarity-based reordering
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.config.settings import settings


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, documents: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        """Rerank documents against a query.

        Returns list of (original_index, score) sorted by score descending, limited to top_k.
        """
        ...


class MockReranker(BaseReranker):
    """Simple cosine-similarity reranker using TF-IDF-like features."""

    async def rerank(self, query: str, documents: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        if not documents:
            return []
        query_tokens = set(query.lower().split())
        scores = []
        for i, doc in enumerate(documents):
            doc_tokens = set(doc.lower().split())
            # Jaccard-like similarity
            intersection = len(query_tokens & doc_tokens)
            union = len(query_tokens | doc_tokens)
            score = intersection / union if union > 0 else 0.0
            scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class LocalReranker(BaseReranker):
    """Local bge-reranker-v2-m3 using CrossEncoder."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    async def rerank(self, query: str, documents: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        if not documents:
            return []
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs).tolist()
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)
        return indexed[:top_k]


def get_reranker() -> BaseReranker:
    """Factory: get reranker based on settings."""
    if settings.reranker_provider == "local":
        return LocalReranker(settings.bge_reranker_model)
    return MockReranker()
