"""Milvus vector store — collection management, insert, and hybrid search."""

from __future__ import annotations

import uuid
from typing import Any

from pymilvus import (
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
)

from src.config.settings import settings
from src.rag.embedder import BaseEmbedder


class MilvusStore:
    """Milvus store for compliance policies and historical decisions."""

    def __init__(self, embedder: BaseEmbedder) -> None:
        self.embedder = embedder
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        )

    def _collection_name(self, name: str) -> str:
        return f"kriterion_{name}"

    def _ensure_collection(self, name: str, dim: int) -> None:
        """Create collection if it doesn't exist."""
        coll_name = self._collection_name(name)
        if self.client.has_collection(coll_name):
            return

        self.client.create_collection(
            collection_name=coll_name,
            dimension=dim,
            metric_type="COSINE",
            auto_id=True,
        )

    async def index_documents(
        self,
        collection_name: str,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Index documents into a Milvus collection."""
        dim = self.embedder.dim if hasattr(self.embedder, "dim") else settings.embedding_dim
        self._ensure_collection(collection_name, dim)

        dense_vecs, sparse_vecs = await self.embedder.embed(texts)
        coll_name = self._collection_name(collection_name)

        data = []
        for i, (vec, text) in enumerate(zip(dense_vecs, texts)):
            row = {
                "vector": vec,
                "text": text,
            }
            if metadatas and i < len(metadatas):
                for k, v in metadatas[i].items():
                    row[f"meta_{k}"] = v
            data.append(row)

        # Insert with dynamic fields enabled
        self.client.insert(collection_name=coll_name, data=data)

    async def hybrid_search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform vector similarity search (hybrid = dense + optional filter)."""
        coll_name = self._collection_name(collection_name)
        if not self.client.has_collection(coll_name):
            return []

        query_vec, _ = await self.embedder.embed_query(query)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10},
        }

        results = self.client.search(
            collection_name=coll_name,
            data=[query_vec],
            limit=top_k,
            search_params=search_params,
            filter=filter_expr,
            output_fields=["text"],
        )

        hits = []
        if results and results[0]:
            for hit in results[0]:
                hits.append({
                    "text": hit.get("entity", {}).get("text", ""),
                    "score": hit.get("distance", 0.0),
                    "id": hit.get("id"),
                })
        return hits
