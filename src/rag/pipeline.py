"""Retrieval pipeline — lexical (BM25) search over the local knowledge base.

Retrieves candidates with BM25, then applies metadata filters (country,
category) before truncation so the compliance and historical knowledge bases
stay precise.
"""

from __future__ import annotations

from typing import Any

from src.rag.bm25_store import get_bm25_store


def _matches(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    """Metadata filter — equality on the listed keys (site / category / rule_type)."""
    if not filters:
        return True
    return all(metadata.get(key) == value for key, value in filters.items() if value is not None)


class HybridRetrievalPipeline:
    """Orchestrates lexical retrieval with metadata filtering."""

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search a collection, applying metadata filters before truncation.

        Returns a list of dicts with keys: text, score, source, metadata.
        """
        store = get_bm25_store(collection_name)
        # Over-retrieve, filter, then truncate so filtering can't starve results.
        candidates = store.search(query, top_k=top_k * 3)

        kept = [c for c in candidates if _matches(c.get("metadata", {}), filters)]
        if not kept and filters:
            # Filters too narrow for this query — fall back to unfiltered hits
            # so the caller still gets context (and can see the filter missed).
            kept = candidates

        return [
            {
                "text": c.get("text", ""),
                "score": c.get("score", 0.0),
                "source": "bm25",
                "metadata": c.get("metadata", {}),
            }
            for c in kept[:top_k]
        ]
