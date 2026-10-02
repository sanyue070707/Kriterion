"""Bulk indexer — build the local BM25 indexes from the generated dataset.

Indexes two collections used by the evidence agents:
  - compliance_policies: regulatory rules per country/category
  - historical_decisions: past verdicts and their lessons learned
"""

from __future__ import annotations

import json
from pathlib import Path

from src.rag.bm25_store import get_bm25_store

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mock"


def _load_json(path: Path) -> list[dict] | dict:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _policy_text(r: dict) -> str:
    text = (
        f"Category: {r['category']}, Country: {r['target_country']}, "
        f"Type: {r['rule_type']}, Severity: {r['severity']}. {r['description']}"
    )
    if r.get("required_certs"):
        text += f" Required certs: {', '.join(r['required_certs'])}"
    if r.get("banned_substances"):
        text += f" Banned: {', '.join(r['banned_substances'])}"
    if r.get("import_duty_pct") is not None:
        text += f" Import duty: {r['import_duty_pct']}%"
    return text


def index_compliance_policies() -> int:
    """Index compliance policies into BM25."""
    records = _load_json(DATA_DIR / "compliance_policies.json")
    if not records:
        return 0

    texts, metadatas = [], []
    for r in records:
        texts.append(_policy_text(r))
        metadatas.append({
            "category": r["category"],
            "target_country": r["target_country"],
            "rule_type": r["rule_type"],
            "severity": r["severity"],
        })

    get_bm25_store("compliance_policies").index(texts, metadatas)
    return len(texts)


def index_historical_decisions() -> int:
    """Index historical decisions into BM25."""
    records = _load_json(DATA_DIR / "historical_decisions.json")
    if not records:
        return 0

    texts, metadatas = [], []
    for r in records:
        snap = r["candidate_snapshot"]
        text = (
            f"Product: {snap['name']}, Category: {snap['category']}, Platform: {snap['platform']}, "
            f"Country: {snap['target_country']}, Price: ${snap['price_usd']}. "
            f"Verdict: {r['verdict']}. {r['key_evidence_summary']}. "
            f"Outcome: {r['outcome_actual']}. Lesson: {r['lessons_learned']}"
        )
        texts.append(text)
        metadatas.append({
            "category": snap["category"],
            "platform": snap["platform"],
            "target_country": snap["target_country"],
            "verdict": r["verdict"],
            "outcome": r["outcome_actual"],
        })

    get_bm25_store("historical_decisions").index(texts, metadatas)
    return len(texts)


def index_all() -> dict[str, int]:
    """Build both BM25 indexes. Returns per-collection document counts."""
    return {
        "compliance_policies": index_compliance_policies(),
        "historical_decisions": index_historical_decisions(),
    }
