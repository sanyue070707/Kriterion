"""Seed PostgreSQL with generated mock data.

Reads JSON files from data/mock/ and data/reference/ and inserts them into the database.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.db.connection import async_session_factory, engine


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"
REF_DIR = DATA_DIR / "reference"


def _load_json(path: Path) -> list[dict] | dict:
    if not path.exists():
        print(f"  ⚠ {path} not found, skipping")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def seed_candidates(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "candidates.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "name": r["name"], "category": r["category"], "subcategory": r.get("subcategory"),
            "platform": r["platform"], "source_country": r["source_country"],
            "target_country": r["target_country"], "price_usd": r.get("price_usd"),
            "currency": r.get("currency", "USD"), "moq": r.get("moq"),
            "weight_kg": r.get("weight_kg"), "status": r.get("status", "pending"),
            "metadata": json.dumps(r.get("metadata", {})),
        })
    await session.execute(text("""
        INSERT INTO candidates (name, category, subcategory, platform, source_country,
            target_country, price_usd, currency, moq, weight_kg, status, metadata)
        VALUES (:name, :category, :subcategory, :platform, :source_country,
            :target_country, :price_usd, :currency, :moq, :weight_kg, :status, :metadata::jsonb)
    """), values)
    return len(values)


async def seed_market_trends(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "market_trends.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "category": r["category"], "platform": r["platform"], "country": r["country"],
            "period_month": r["period_month"], "search_volume": r.get("search_volume"),
            "growth_rate_pct": r.get("growth_rate_pct"), "avg_rating": r.get("avg_rating"),
            "review_count": r.get("review_count"),
            "top_keywords": r.get("top_keywords", []),
            "influencer_mentions": r.get("influencer_mentions", 0),
            "creator_sellers": r.get("creator_sellers", 0),
            "avg_monthly_revenue_usd": r.get("avg_monthly_revenue_usd"),
        })
    await session.execute(text("""
        INSERT INTO market_trends (category, platform, country, period_month, search_volume,
            growth_rate_pct, avg_rating, review_count, top_keywords, influencer_mentions,
            creator_sellers, avg_monthly_revenue_usd)
        VALUES (:category, :platform, :country, :period_month::date, :search_volume,
            :growth_rate_pct, :avg_rating, :review_count, :top_keywords::text[], :influencer_mentions,
            :creator_sellers, :avg_monthly_revenue_usd)
    """), values)
    return len(values)


async def seed_supplier_quotes(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "supplier_quotes.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "supplier_id": r["supplier_id"], "category": r["category"],
            "source_country": r["source_country"], "unit_price_usd": r["unit_price_usd"],
            "moq": r["moq"], "lead_time_days": r["lead_time_days"],
            "freight_mode": r["freight_mode"], "freight_cost_per_kg": r.get("freight_cost_per_kg"),
            "port_of_origin": r.get("port_of_origin"),
        })
    await session.execute(text("""
        INSERT INTO supplier_quotes (supplier_id, category, source_country, unit_price_usd,
            moq, lead_time_days, freight_mode, freight_cost_per_kg, port_of_origin)
        VALUES (:supplier_id, :category, :source_country, :unit_price_usd,
            :moq, :lead_time_days, :freight_mode, :freight_cost_per_kg, :port_of_origin)
    """), values)
    return len(values)


async def seed_compliance_policies(session: AsyncSession) -> int:
    records = _load_json(MOCK_DIR / "compliance_policies.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "category": r["category"], "target_country": r["target_country"],
            "rule_type": r["rule_type"], "description": r["description"],
            "severity": r["severity"],
            "required_certs": r.get("required_certs", []),
            "banned_substances": r.get("banned_substances", []),
            "import_duty_pct": r.get("import_duty_pct"),
        })
    await session.execute(text("""
        INSERT INTO compliance_policies (category, target_country, rule_type, description,
            severity, required_certs, banned_substances, import_duty_pct)
        VALUES (:category, :target_country, :rule_type, :description,
            :severity, :required_certs::text[], :banned_substances::text[], :import_duty_pct)
    """), values)
    return len(values)


async def seed_trademarks(session: AsyncSession) -> int:
    records = _load_json(REF_DIR / "trademark_sample.json")
    if not records:
        return 0
    values = []
    for r in records:
        values.append({
            "name": r["name"], "category": r.get("category"), "country": r["country"],
            "status": r["status"], "owner": r.get("owner"),
        })
    await session.execute(text("""
        INSERT INTO trademarks (name, category, country, status, owner)
        VALUES (:name, :category, :country, :status, :owner)
    """), values)
    return len(values)


async def main() -> None:
    async with async_session_factory() as session:
        print("Seeding candidates...")
        n = await seed_candidates(session)
        print(f"  → {n} candidates")

        print("Seeding market trends...")
        n = await seed_market_trends(session)
        print(f"  → {n} market trends")

        print("Seeding supplier quotes...")
        n = await seed_supplier_quotes(session)
        print(f"  → {n} supplier quotes")

        print("Seeding compliance policies...")
        n = await seed_compliance_policies(session)
        print(f"  → {n} compliance policies")

        print("Seeding trademarks...")
        n = await seed_trademarks(session)
        print(f"  → {n} trademarks")

        await session.commit()
        print("\n✅ Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
