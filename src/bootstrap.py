"""One-shot, idempotent bootstrap.

Safe to call from the CLI, the API lifespan, or repeatedly by hand. It:
  1. generates the dataset files if missing,
  2. creates the SQLite schema,
  3. seeds the tables if empty,
  4. builds the BM25 retrieval indexes,
  5. adds a few curated sample candidates so the picker always has interesting
     cases (a clean one, a compliance-blocked one, and one the funnel rejects).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import case, func, select

from src.config.settings import settings
from src.db.connection import async_session_factory, init_db
from src.db.models import Candidate, CompliancePolicy
from src.rag.indexer import index_all

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DATA_DIR = ROOT / settings.data_dir


def _load_script(name: str):
    """Import a sibling script module by file path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_data_files() -> bool:
    """Generate the dataset if it's missing. Returns True if it was generated."""
    if (DATA_DIR / "mock" / "candidates.json").exists():
        return False
    _load_script("generate_mock_data").main()
    return True


async def _candidate_count(session) -> int:
    return (await session.execute(select(func.count()).select_from(Candidate))).scalar() or 0


async def _pick_combo(session, want_block: bool) -> tuple[str, str]:
    """Pick a (category, target_country) with blocking policies present/absent."""
    blocks = func.sum(case((CompliancePolicy.severity == "block", 1), else_=0)).label("blocks")
    rows = (
        await session.execute(
            select(CompliancePolicy.category, CompliancePolicy.target_country, blocks)
            .group_by(CompliancePolicy.category, CompliancePolicy.target_country)
            .order_by(blocks.desc())
        )
    ).all()
    if not rows:
        return ("beauty", "US")
    if want_block:
        return (rows[0].category, rows[0].target_country)
    clear = [r for r in rows if r.blocks == 0]
    return (clear[0].category, clear[0].target_country) if clear else (rows[-1].category, rows[-1].target_country)


async def _add_curated_candidates(session) -> int:
    """Add labelled sample candidates (skipping any that already exist)."""
    existing = set((await session.execute(select(Candidate.name))).scalars().all())
    clear = await _pick_combo(session, want_block=False)
    blocked = await _pick_combo(session, want_block=True)

    specs = [
        {"name": "Sample: Clear-Compliance Bestseller", "category": clear[0], "target_country": clear[1],
         "platform": "tiktok_shop", "source_country": "CN", "price_usd": 39.99, "weight_kg": 0.4},
        {"name": "Sample: Compliance-Blocked Listing", "category": blocked[0], "target_country": blocked[1],
         "platform": "tiktok_shop", "source_country": "CN", "price_usd": 24.99, "weight_kg": 0.3},
        {"name": "Sample: Screening Reject (Overpriced)", "category": "electronics", "target_country": "US",
         "platform": "shopee", "source_country": "CN", "price_usd": 899.0, "weight_kg": 2.0},
    ]

    created = 0
    for spec in specs:
        if spec["name"] in existing:
            continue
        session.add(Candidate(
            name=spec["name"],
            category=spec["category"],
            subcategory=f"{spec['category']}_sample",
            platform=spec["platform"],
            source_country=spec["source_country"],
            target_country=spec["target_country"],
            price_usd=spec["price_usd"],
            currency="USD",
            moq=200,
            weight_kg=spec["weight_kg"],
            status="pending",
            metadata_={"sample": True},
        ))
        created += 1
    return created


async def bootstrap(verbose: bool = True) -> dict:
    """Prepare data, schema, seed rows, retrieval indexes, and sample candidates."""
    report: dict = {}

    report["data_generated"] = ensure_data_files()

    await init_db()

    seed_module = _load_script("seed_database")
    async with async_session_factory() as session:
        if await _candidate_count(session) == 0:
            report["seeded"] = await seed_module.seed_all(session)
        else:
            report["seeded"] = None
        report["curated_added"] = await _add_curated_candidates(session)
        await session.commit()

    report["indexed"] = index_all()
    report["total_candidates"] = await _count_candidates()

    if verbose:
        if report["data_generated"]:
            print("  generated dataset")
        if report["seeded"]:
            print(f"  seeded database: {report['seeded']}")
        if report["curated_added"]:
            print(f"  added {report['curated_added']} sample candidates")
        print(f"  indexed: {report['indexed']}")
        print(f"  candidates available: {report['total_candidates']}")
    return report


async def _count_candidates() -> int:
    async with async_session_factory() as session:
        return await _candidate_count(session)
