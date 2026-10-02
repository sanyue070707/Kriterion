"""Run detail endpoint — everything about one evaluation in a single call."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DecisionCardResponse, EvidenceItemResponse, RunDetailResponse
from src.db.connection import get_session
from src.db.repository import get_decision_card_by_run, get_workflow_run, query_evidence_by_run

router = APIRouter(prefix="/runs", tags=["runs"])


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_detail_endpoint(run_id: str, session: AsyncSession = Depends(get_session)):
    """Return the decision card, evidence ledger, gatekeeper report, and tool trace."""
    run = await get_workflow_run(session, uuid.UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    card = await get_decision_card_by_run(session, uuid.UUID(run_id))
    evidence = await query_evidence_by_run(session, uuid.UUID(run_id))

    card_response = None
    if card is not None:
        card_response = DecisionCardResponse(
            id=str(card.id),
            run_id=str(card.run_id),
            candidate_id=str(card.candidate_id),
            candidate_name=card.candidate_name,
            verdict=card.verdict,
            scores=card.scores,
            overall_score=float(card.overall_score),
            unit_economics=card.unit_economics,
            evidence_summary=card.evidence_summary,
            risk_flags=card.risk_flags,
            watch_reasons=card.watch_reasons,
            decided_at=card.decided_at.isoformat(),
        )

    evidence_response = [
        EvidenceItemResponse(
            id=str(e.id),
            agent_type=e.agent_type,
            dimension=e.dimension,
            claim=e.claim,
            value=float(e.value) if e.value is not None else None,
            unit=e.unit,
            source_tool=e.source_tool,
            source_url=e.source_url,
            fetch_time=_iso(e.fetch_time),
            validity_until=_iso(e.validity_until),
            confidence=float(e.confidence) if e.confidence is not None else 0.0,
            raw_response=e.raw_response,
        )
        for e in evidence
    ]

    return RunDetailResponse(
        run_id=str(run.id),
        status=run.status,
        candidate_id=str(run.candidate_id),
        candidate_name=card.candidate_name if card else None,
        screening_passed=run.screening_passed,
        screening_reason=run.screening_reason,
        decision_card=card_response,
        evidence=evidence_response,
        gatekeeper_report=card.gatekeeper_report if card else None,
        tool_trace=(card.tool_trace or []) if card else [],
    )
