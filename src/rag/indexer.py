"""Bulk indexer — index compliance policies and historical decisions into Milvus + BM25."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.rag.bm25_store import get_bm25_store
from src.rag.embedder import get_embedder
from src.rag.milvus_store import MilvusStore


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mock"


def _load_json(path: Path) -> list[dict] | dict:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def index_compliance_policies(store: MilvusStore) -> int:
    """Index compliance policies into both Milvus and BM25."""
    records = _load_json(DATA_DIR / "compliance_policies.json")
    if not records:
        return 0

    texts, metadatas = [], []
    for r in records:
        text = f"Category: {r['category']}, Country: {r['target_country']}, Type: {r['rule_type']}, Severity: {r['severity']}. {r['description']}"
        if r.get("required_certs"):
            text += f" Required certs: {', '.join(r['required_certs'])}"
        if r.get("banned_substances"):
            text += f" Banned: {', '.join(r['banned_substances'])}"
        if r.get("import_duty_pct") is not None:
            text += f" Import duty: {r['import_duty_pct']}%"
        texts.append(text)
        metadatas.append({
            "category": r["category"],
            "target_country": r["target_country"],
            "rule_type": r["rule_type"],
            "severity": r["severity"],
        })

    # Milvus
    await store.index_documents("compliance_policies", texts, metadatas)

    # BM25
    bm25 = get_bm25_store("compliance_policies")
    bm25.index(texts, metadatas)

    return len(texts)


async def index_historical_decisions(store: MilvusStore) -> int:
    """Index historical decisions into both Milvus and BM25."""
    records = _load_json(DATA_DIR / "historical_decisions.json")
    if not records:
        return 0

    texts, metadatas = [], []
    for r in records:
        snap = r["candidate_snapshot"]
        text = f"Product: {snap['name']}, Category: {snap['category']}, Platform: {snap['platform']}, Country: {snap['target_country']}, Price: ${snap['price_usd']}. "
        text += f"Verdict: {r['verdict']}. {r['key_evidence_summary']}. Outcome: {r['outcome_actual']}. Lesson: {r['lessons_learned']}"
        texts.append(text)
        metadatas.append({
            "category": snap["category"],
            "platform": snap["platform"],
            "target_country": snap["target_country"],
            "verdict": r["verdict"],
            "outcome": r["outcome_actual"],
        })

    # Milvus
    await store.index_documents("historical_decisions", texts, metadatas)

    # BM25
    bm25 = get_bm25_store("historical_decisions")
    bm25.index(texts, metadatas)

    return len(texts)


async def index_all() -> None:
    """Index all collections."""
    embedder = get_embedder()
    store = MilvusStore(embedder=embedder)

    n = await index_compliance_policies(store)
    print(f"Indexed {n} compliance policies")

    n = await index_historical_decisions(store)
    print(f"Indexed {n} historical decisions")
