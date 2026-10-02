"""Data access layer — CRUD operations for all tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Candidate,
    CompliancePolicy,
    DecisionCard,
    EvidenceItem,
    MarketTrend,
    ScreeningResult,
    SupplierQuote,
    Trademark,
    WorkflowRun,
)


# ── Candidates ──


async def create_candidate(session: AsyncSession, **kwargs: Any) -> Candidate:
    obj = Candidate(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


async def get_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> Candidate | None:
    return await session.get(Candidate, candidate_id)


async def list_candidates(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[Candidate]:
    result = await session.execute(select(Candidate).order_by(Candidate.created_at.desc()).limit(limit).offset(offset))
    return list(result.scalars().all())


async def update_candidate_status(session: AsyncSession, candidate_id: uuid.UUID, status: str) -> None:
    await session.execute(update(Candidate).where(Candidate.id == candidate_id).values(status=status))


# ── Screening ──


async def create_screening_result(session: AsyncSession, **kwargs: Any) -> ScreeningResult:
    obj = ScreeningResult(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


# ── Market Trends ──


async def query_market_trends(
    session: AsyncSession,
    category: str,
    platform: str,
    country: str,
    limit: int = 12,
) -> list[MarketTrend]:
    result = await session.execute(
        select(MarketTrend)
        .where(MarketTrend.category == category, MarketTrend.platform == platform, MarketTrend.country == country)
        .order_by(MarketTrend.period_month.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Supplier Quotes ──


async def query_supplier_quotes(
    session: AsyncSession,
    category: str,
    source_country: str,
) -> list[SupplierQuote]:
    result = await session.execute(
        select(SupplierQuote).where(SupplierQuote.category == category, SupplierQuote.source_country == source_country)
    )
    return list(result.scalars().all())


# ── Compliance Policies ──


async def query_compliance_policies(
    session: AsyncSession,
    category: str,
    target_country: str,
) -> list[CompliancePolicy]:
    result = await session.execute(
        select(CompliancePolicy).where(CompliancePolicy.category == category, CompliancePolicy.target_country == target_country)
    )
    return list(result.scalars().all())


# ── Trademarks ──


async def query_trademarks(
    session: AsyncSession,
    name: str,
    country: str,
) -> list[Trademark]:
    result = await session.execute(select(Trademark).where(Trademark.name.ilike(f"%{name}%"), Trademark.country == country))
    return list(result.scalars().all())


# ── Evidence Items ──


async def create_evidence_item(session: AsyncSession, **kwargs: Any) -> EvidenceItem:
    obj = EvidenceItem(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


async def query_evidence_by_run(session: AsyncSession, run_id: uuid.UUID) -> list[EvidenceItem]:
    result = await session.execute(select(EvidenceItem).where(EvidenceItem.run_id == run_id))
    return list(result.scalars().all())


# ── Decision Cards ──


async def create_decision_card(session: AsyncSession, **kwargs: Any) -> DecisionCard:
    obj = DecisionCard(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


async def get_decision_card(session: AsyncSession, card_id: uuid.UUID) -> DecisionCard | None:
    return await session.get(DecisionCard, card_id)


async def get_decision_card_by_run(session: AsyncSession, run_id: uuid.UUID) -> DecisionCard | None:
    result = await session.execute(select(DecisionCard).where(DecisionCard.run_id == run_id))
    return result.scalar_one_or_none()


async def list_decision_cards(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[DecisionCard]:
    result = await session.execute(select(DecisionCard).order_by(DecisionCard.decided_at.desc()).limit(limit).offset(offset))
    return list(result.scalars().all())


# ── Workflow Runs ──


async def create_workflow_run(session: AsyncSession, **kwargs: Any) -> WorkflowRun:
    obj = WorkflowRun(**kwargs)
    session.add(obj)
    await session.flush()
    return obj


async def get_workflow_run(session: AsyncSession, run_id: uuid.UUID) -> WorkflowRun | None:
    return await session.get(WorkflowRun, run_id)


async def update_workflow_run(session: AsyncSession, run_id: uuid.UUID, **kwargs: Any) -> None:
    await session.execute(update(WorkflowRun).where(WorkflowRun.id == run_id).values(**kwargs))
