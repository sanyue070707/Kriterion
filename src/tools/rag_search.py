"""RAG search tool — shared across all agents.

Runs lexical (BM25) retrieval over the local knowledge base with optional
metadata filtering (site / category).
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from src.rag.pipeline import HybridRetrievalPipeline
from src.tools.provenance import _ref

_pipeline: HybridRetrievalPipeline | None = None


def _get_pipeline() -> HybridRetrievalPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = HybridRetrievalPipeline()
    return _pipeline


@tool
async def hybrid_search(
    query: str,
    collection: str = "compliance_policies",
    top_k: int = 5,
    filters: dict | None = None,
) -> dict:
    """Perform hybrid search (lexical + metadata filter) across the knowledge base.

    Args:
        query: Search query text
        collection: Collection to search - 'compliance_policies' or 'historical_decisions'
        top_k: Number of results to return
        filters: Optional metadata filter, e.g. {"target_country": "US", "category": "beauty"}

    Returns the most relevant document chunks with scores.
    """
    pipeline = _get_pipeline()
    results = await pipeline.search(
        query=query,
        collection_name=collection,
        top_k=top_k,
        filters=filters,
    )

    return {
        "query": query,
        "collection": collection,
        "results": [
            {
                "text": r["text"][:200],
                "score": round(r["score"], 4),
                "metadata": r.get("metadata", {}),
                "source": r.get("source", "unknown"),
            }
            for r in results
        ],
        "total_found": len(results),
        "source_url": _ref("bm25", collection, {"query": query}),
        "fetch_time": datetime.now().isoformat(),
    }
