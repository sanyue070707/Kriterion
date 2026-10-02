"""Seed Milvus vector store with compliance policies and historical decisions for RAG.

Indexes documents from data/mock/ into Milvus collections:
  - compliance_policies: for compliance risk agent RAG
  - historical_decisions: for decision review agent context
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.rag.embedder import get_embedder
from src.rag.milvus_store import MilvusStore


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"


def _load_json(path: Path) -> list[dict] | dict:
    if not path.exists():
        print(f"  ⚠ {path} not found, skipping")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def seed_compliance_collection(store: MilvusStore) -> int:
    """Index compliance policies into Milvus."""
    records = _load_json(MOCK_DIR / "compliance_policies.json")
    if not records:
        return 0

    texts = []
    metadatas = []
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

    await store.index_documents(
        collection_name="compliance_policies",
        texts=texts,
        metadatas=metadatas,
    )
    return len(texts)


async def seed_historical_collection(store: MilvusStore) -> int:
    """Index historical decisions into Milvus."""
    records = _load_json(MOCK_DIR / "historical_decisions.json")
    if not records:
        return 0

    texts = []
    metadatas = []
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

    await store.index_documents(
        collection_name="historical_decisions",
        texts=texts,
        metadatas=metadatas,
    )
    return len(texts)


async def main() -> None:
    embedder = get_embedder()
    store = MilvusStore(embedder=embedder)

    print("Seeding compliance policies into Milvus...")
    n = await seed_compliance_collection(store)
    print(f"  → {n} compliance policies indexed")

    print("Seeding historical decisions into Milvus...")
    n = await seed_historical_collection(store)
    print(f"  → {n} historical decisions indexed")

    print("\n✅ Vector store seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
