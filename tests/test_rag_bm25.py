"""Tests for the dependency-free BM25 store and retrieval pipeline."""

from src.rag.bm25_store import BM25Store
from src.rag.pipeline import HybridRetrievalPipeline

DOCS = [
    "Category: beauty, Country: US. requires FDA certification",
    "Category: electronics, Country: US. requires FCC UL certification",
    "Category: toys, Country: US. requires CPSC ASTM safety testing",
]
META = [
    {"category": "beauty", "target_country": "US"},
    {"category": "electronics", "target_country": "US"},
    {"category": "toys", "target_country": "UK"},
]


class TestBM25Store:
    def test_index_and_search_ranks_relevant_doc(self):
        store = BM25Store()
        store.index(DOCS)
        hits = store.search("FDA certification beauty", top_k=3)
        assert hits
        assert "beauty" in hits[0]["text"]
        assert store.size == 3

    def test_empty_store_returns_nothing(self):
        assert BM25Store().search("anything") == []

    def test_irrelevant_query_yields_no_hits(self):
        store = BM25Store()
        store.index(DOCS)
        assert store.search("zzzzz nonexistenttoken") == []


class TestPipeline:
    async def test_metadata_filter_applied(self):
        store = BM25Store()
        store.index(DOCS, META)
        # Inject into the pipeline's collection so it searches our docs.
        from src.rag import bm25_store as mod
        mod._bm25_stores["test_policies"] = store

        pipeline = HybridRetrievalPipeline()
        hits = await pipeline.search("certification", "test_policies", top_k=3,
                                     filters={"target_country": "US"})
        assert hits
        assert all(h["metadata"]["target_country"] == "US" for h in hits)
