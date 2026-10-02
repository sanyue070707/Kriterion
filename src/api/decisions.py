"""Decisions API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DecisionCardListResponse, DecisionCardResponse
from src.db.connection import get_session
from src.db.models import DecisionCard
from src.db.repository import get_decision_card, get_decision_card_by_run, list_decision_cards

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _to_response(c: DecisionCard) -> DecisionCardResponse:
    return DecisionCardResponse(
        id=str(c.id),
        run_id=str(c.run_id),
        candidate_id=str(c.candidate_id),
        candidate_name=c.candidate_name,
        verdict=c.verdict,
        scores=c.scores,
        overall_score=float(c.overall_score),
        unit_economics=c.unit_economics,
        evidence_summary=c.evidence_summary,
        risk_flags=c.risk_flags,
        watch_reasons=c.watch_reasons,
        decided_at=c.decided_at.isoformat(),
    )


@router.get("", response_model=DecisionCardListResponse)
async def list_decisions_endpoint(
    limit: int = 50,
    offset: int = 0,
    run_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List decision cards, optionally filtered to a single run."""
    if run_id:
        card = await get_decision_card_by_run(session, uuid.UUID(run_id))
        items = [_to_response(card)] if card else []
        return DecisionCardListResponse(items=items, total=len(items))

    cards = await list_decision_cards(session, limit=limit, offset=offset)
    items = [_to_response(c) for c in cards]
    return DecisionCardListResponse(items=items, total=len(items))


@router.get("/{card_id}", response_model=DecisionCardResponse)
async def get_decision_endpoint(card_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific decision card by ID."""
    card = await get_decision_card(session, uuid.UUID(card_id))
    if not card:
        raise HTTPException(status_code=404, detail="Decision card not found")
    return _to_response(card)
