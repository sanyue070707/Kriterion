"""RAG search tool — shared across all agents."""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from src.rag.pipeline import HybridRetrievalPipeline

_pipeline: HybridRetrievalPipeline | None = None


def _get_pipeline() -> HybridRetrievalPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = HybridRetrievalPipeline()
    return _pipeline


@tool
async def hybrid_search(query: str, collection: str = "compliance_policies", top_k: int = 5) -> dict:
    """Perform hybrid search (vector + BM25 + rerank) across the knowledge base.

    Args:
        query: Search query text
        collection: Collection to search - 'compliance_policies' or 'historical_decisions'
        top_k: Number of results to return

    Returns most relevant document chunks with scores.
    """
    pipeline = _get_pipeline()
    results = await pipeline.search(
        query=query,
        collection_name=collection,
        top_k=top_k,
    )

    return {
        "query": query,
        "collection": collection,
        "results": [
            {"text": r["text"][:200], "score": round(r["score"], 4), "source": r.get("source", "unknown")}
            for r in results
        ],
        "total_found": len(results),
        "fetch_time": datetime.now().isoformat(),
    }
