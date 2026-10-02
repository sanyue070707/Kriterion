"""Decisions API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DecisionCardListResponse, DecisionCardResponse
from src.db.connection import get_session
from src.db.repository import get_decision_card, list_decision_cards

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=DecisionCardListResponse)
async def list_decisions_endpoint(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """List decision cards."""
    cards = await list_decision_cards(session, limit=limit, offset=offset)
    items = [
        DecisionCardResponse(
            id=str(c.id),
            run_id=str(c.run_id),
            candidate_id=str(c.candidate_id),
            verdict=c.verdict,
            scores=c.scores,
            overall_score=float(c.overall_score),
            unit_economics=c.unit_economics,
            evidence_summary=c.evidence_summary,
            risk_flags=c.risk_flags,
            watch_reasons=c.watch_reasons,
            decided_at=c.decided_at.isoformat(),
        )
        for c in cards
    ]
    return DecisionCardListResponse(items=items, total=len(items))


@router.get("/{card_id}", response_model=DecisionCardResponse)
async def get_decision_endpoint(
    card_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific decision card by ID."""
    c = await get_decision_card(session, uuid.UUID(card_id))
    if not c:
        raise HTTPException(status_code=404, detail="Decision card not found")
    return DecisionCardResponse(
        id=str(c.id),
        run_id=str(c.run_id),
        candidate_id=str(c.candidate_id),
        verdict=c.verdict,
        scores=c.scores,
        overall_score=float(c.overall_score),
        unit_economics=c.unit_economics,
        evidence_summary=c.evidence_summary,
        risk_flags=c.risk_flags,
        watch_reasons=c.watch_reasons,
        decided_at=c.decided_at.isoformat(),
    )
