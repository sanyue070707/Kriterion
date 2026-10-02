"""Hybrid retrieval pipeline — embed → Milvus + BM25 → rerank."""

from __future__ import annotations

from typing import Any

from src.rag.bm25_store import get_bm25_store
from src.rag.embedder import get_embedder
from src.rag.milvus_store import MilvusStore
from src.rag.reranker import get_reranker


class HybridRetrievalPipeline:
    """Orchestrates hybrid retrieval: vector search + BM25 + reranking."""

    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.milvus = MilvusStore(embedder=self.embedder)
        self.reranker = get_reranker()

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        filter_expr: str | None = None,
        use_milvus: bool = True,
        use_bm25: bool = True,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search across Milvus + BM25, then rerank.

        Returns list of dicts with keys: text, score, source (milvus/bm25).
        """
        candidates: list[dict[str, Any]] = []

        # 1. Vector search via Milvus
        if use_milvus:
            try:
                milvus_results = await self.milvus.hybrid_search(
                    collection_name=collection_name,
                    query=query,
                    top_k=top_k * 2,  # over-retrieve before reranking
                    filter_expr=filter_expr,
                )
                for r in milvus_results:
                    candidates.append({**r, "source": "milvus"})
            except Exception as e:
                # Milvus unavailable — fall back to BM25 only
                print(f"Milvus search failed: {e}, using BM25 only")

        # 2. BM25 search
        if use_bm25:
            bm25_store = get_bm25_store(collection_name)
            bm25_results = bm25_store.search(query, top_k=top_k * 2)
            for r in bm25_results:
                candidates.append({**r, "source": "bm25"})

        if not candidates:
            return []

        # 3. Deduplicate by text
        seen_texts: set[str] = set()
        unique_candidates: list[dict[str, Any]] = []
        for c in candidates:
            text = c.get("text", "")
            if text not in seen_texts:
                seen_texts.add(text)
                unique_candidates.append(c)

        # 4. Rerank
        texts = [c.get("text", "") for c in unique_candidates]
        reranked = await self.reranker.rerank(query, texts, top_k=top_k)

        # 5. Build final results
        results = []
        for idx, score in reranked:
            c = unique_candidates[idx]
            results.append({
                "text": c.get("text", ""),
                "score": score,
                "source": c.get("source", "unknown"),
                "metadata": c.get("metadata", {}),
            })

        return results
