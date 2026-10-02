"""Seed the local database with the generated dataset.

Reads JSON files from data/mock/ and data/reference/ and inserts them via the
SQLAlchemy ORM, so the same code runs on SQLite or PostgreSQL.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import async_session_factory, init_db
from src.db.models import (
    Candidate,
    CompliancePolicy,
    MarketTrend,
    SupplierQuote,
    Trademark,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"
REF_DIR = DATA_DIR / "reference"


def _load_json(path: Path) -> list[dict] | dict:
    if not path.exists():
        print(f"  [WARN] {path} not found, skipping")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def seed_candidates(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "candidates.json")
    if not records:
        return 0
    values = [
        {
            "name": r["name"],
            "category": r["category"],
            "subcategory": r.get("subcategory"),
            "platform": r["platform"],
            "source_country": r["source_country"],
            "target_country": r["target_country"],
            "price_usd": r.get("price_usd"),
            "currency": r.get("currency", "USD"),
            "moq": r.get("moq"),
            "weight_kg": r.get("weight_kg"),
            "status": r.get("status", "pending"),
            "metadata_": r.get("metadata", {}),
        }
        for r in records
    ]
    await session.execute(insert(Candidate), values)
    return len(values)


async def seed_market_trends(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "market_trends.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "category": r["category"],
            "platform": r["platform"],
            "country": r["country"],
            "period_month": datetime.strptime(r["period_month"], "%Y-%m-%d"),
            "search_volume": r.get("search_volume"),
            "growth_rate_pct": r.get("growth_rate_pct"),
            "avg_rating": r.get("avg_rating"),
            "review_count": r.get("review_count"),
            "top_keywords": r.get("top_keywords", []),
            "influencer_mentions": r.get("influencer_mentions", 0),
            "creator_sellers": r.get("creator_sellers", 0),
            "avg_monthly_revenue_usd": r.get("avg_monthly_revenue_usd"),
        })
    await session.execute(insert(MarketTrend), values)
    return len(values)


async def seed_supplier_quotes(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "supplier_quotes.json")
    if not records:
        return 0
    values = [
        {
            "supplier_id": r["supplier_id"],
            "category": r["category"],
            "source_country": r["source_country"],
            "unit_price_usd": r["unit_price_usd"],
            "moq": r["moq"],
            "lead_time_days": r["lead_time_days"],
            "freight_mode": r["freight_mode"],
            "freight_cost_per_kg": r.get("freight_cost_per_kg"),
            "port_of_origin": r.get("port_of_origin"),
        }
        for r in records
    ]
    await session.execute(insert(SupplierQuote), values)
    return len(values)


async def seed_compliance_policies(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "compliance_policies.json")
    if not records:
        return 0
    values = [
        {
            "category": r["category"],
            "target_country": r["target_country"],
            "rule_type": r["rule_type"],
            "description": r["description"],
            "severity": r["severity"],
            "required_certs": r.get("required_certs", []),
            "banned_substances": r.get("banned_substances", []),
            "import_duty_pct": r.get("import_duty_pct"),
        }
        for r in records
    ]
    await session.execute(insert(CompliancePolicy), values)
    return len(values)


async def seed_trademarks(session: AsyncSession) -> int:
    records = _load_json(REF_DIR / "trademark_sample.json")
    if not records:
        return 0
    values = [
        {
            "name": r["name"],
            "category": r.get("category"),
            "country": r["country"],
            "status": r["status"],
            "owner": r.get("owner"),
        }
        for r in records
    ]
    await session.execute(insert(Trademark), values)
    return len(values)


async def is_seeded(session: AsyncSession) -> bool:
    """True if the candidates table already has rows."""
    result = await session.execute(select(func.count()).select_from(Candidate))
    return bool(result.scalar())


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """Seed every table and return per-table row counts."""
    counts = {
        "candidates": await seed_candidates(session),
        "market_trends": await seed_market_trends(session),
        "supplier_quotes": await seed_supplier_quotes(session),
        "compliance_policies": await seed_compliance_policies(session),
        "trademarks": await seed_trademarks(session),
    }
    await session.commit()
    return counts


async def main() -> None:
    await init_db()
    async with async_session_factory() as session:
        if await is_seeded(session):
            print("Database already seeded -- skipping.")
            return
        counts = await seed_all(session)
    for table, n in counts.items():
        print(f"  -> {n} {table}")
    print("\n[OK] Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
