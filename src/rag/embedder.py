"""BGE-M3 embedding wrapper — dense + sparse embeddings.

Supports two modes:
- "local": Uses sentence-transformers to load BAAI/bge-m3
- "mock": Returns random vectors (for demo without GPU)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from src.config.settings import settings


class BaseEmbedder(ABC):
    """Abstract embedder interface."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> tuple[list[list[float]], list[dict[str, Any]]]:
        """Embed texts, returning (dense_vectors, sparse_dicts).

        Each sparse_dict has keys "indices" (list[int]) and "values" (list[float]).
        """
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> tuple[list[float], dict[str, Any]]:
        """Embed a single query text."""
        ...


class MockEmbedder(BaseEmbedder):
    """Random vector embedder for demo/testing."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self._rng = np.random.default_rng(42)

    async def embed(self, texts: list[str]) -> tuple[list[list[float]], list[dict[str, Any]]]:
        dense = [self._random_unit_vector() for _ in texts]
        sparse = [self._random_sparse() for _ in texts]
        return dense, sparse

    async def embed_query(self, text: str) -> tuple[list[float], dict[str, Any]]:
        dense, sparse = await self.embed([text])
        return dense[0], sparse[0]

    def _random_unit_vector(self) -> list[float]:
        v = self._rng.standard_normal(self.dim).astype(np.float32)
        v /= np.linalg.norm(v)
        return v.tolist()

    def _random_sparse(self) -> dict[str, Any]:
        n_tokens = self._rng.integers(5, 20)
        indices = self._rng.integers(0, 50000, size=n_tokens).tolist()
        values = self._rng.uniform(0.1, 1.0, size=n_tokens).astype(np.float32).tolist()
        return {"indices": indices, "values": values}


class LocalEmbedder(BaseEmbedder):
    """Local BGE-M3 embedder using sentence-transformers."""

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    async def embed(self, texts: list[str]) -> tuple[list[list[float]], list[dict[str, Any]]]:
        # BGE-M3 supports dense + sparse via FlagEmbedding
        # For sentence-transformers, we get dense only; sparse is approximated
        dense_vectors = self.model.encode(texts, normalize_embeddings=True).tolist()
        sparse_dicts = [self._approx_sparse(text) for text in texts]
        return dense_vectors, sparse_dicts

    async def embed_query(self, text: str) -> tuple[list[float], dict[str, Any]]:
        dense, sparse = await self.embed([text])
        return dense[0], sparse[0]

    def _approx_sparse(self, text: str) -> dict[str, Any]:
        """Approximate sparse encoding by token hashing."""
        tokens = text.lower().split()[:50]
        indices = [hash(t) % 50000 for t in tokens]
        values = [1.0 / (i + 1) for i in range(len(tokens))]
        return {"indices": indices, "values": values}


def get_embedder() -> BaseEmbedder:
    """Factory: get embedder based on settings."""
    if settings.embedding_provider == "local":
        return LocalEmbedder(settings.bge_m3_model)
    return MockEmbedder(dim=settings.embedding_dim)
