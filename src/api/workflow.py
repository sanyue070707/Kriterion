"""Workflow API endpoints — trigger and monitor evaluations."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import WorkflowRunRequest, WorkflowRunResponse, WorkflowStatusResponse
from src.db.connection import async_session_factory, get_session
from src.db.repository import (
    create_decision_card,
    create_evidence_item,
    create_workflow_run,
    get_candidate,
    get_workflow_run,
    update_candidate_status,
    update_workflow_run,
)
from src.service.evaluate import candidate_to_raw, run_evaluation

router = APIRouter(prefix="/workflow", tags=["workflow"])


async def _run_workflow_background(run_id_str: str, candidate_id_str: str) -> None:
    """Execute the evaluation workflow in the background and persist results."""
    async with async_session_factory() as session:
        candidate = await get_candidate(session, uuid.UUID(candidate_id_str))
        if not candidate:
            return
        candidate_raw = candidate_to_raw(candidate)

    try:
        result = await run_evaluation(candidate_raw, run_id_str)
    except Exception as exc:  # noqa: BLE001 - surface the failure to the client
        async with async_session_factory() as session:
            await update_workflow_run(
                session, uuid.UUID(run_id_str), status="failed", error_message=str(exc)[:500]
            )
            await session.commit()
        return

    async with async_session_factory() as session:
        for item in result.gated_evidence:
            await create_evidence_item(
                session,
                run_id=uuid.UUID(run_id_str),
                candidate_id=uuid.UUID(candidate_id_str),
                agent_type=item.agent_type.value,
                dimension=item.dimension.value,
                claim=item.claim,
                value=item.value,
                unit=item.unit,
                source_tool=item.source_tool,
                source_url=item.source_url,
                fetch_time=item.fetch_time,
                validity_until=item.validity_until,
                confidence=item.confidence,
                raw_response=item.raw_response,
            )

        card = result.decision_card
        if card is not None:
            await create_decision_card(
                session,
                run_id=uuid.UUID(run_id_str),
                candidate_id=uuid.UUID(candidate_id_str),
                candidate_name=card.candidate_name,
                verdict=card.verdict,
                scores=card.scores,
                overall_score=card.overall_score,
                unit_economics=card.unit_economics,
                evidence_summary=card.evidence_summary,
                risk_flags=card.risk_flags,
                watch_reasons=card.watch_reasons,
                gatekeeper_report=result.gatekeeper_report,
                tool_trace=result.tool_trace,
            )
            new_status = "decided" if card.verdict in ("go", "no_go") else "watch"
            await update_candidate_status(session, uuid.UUID(candidate_id_str), new_status)
        elif result.screening_passed is False:
            await update_candidate_status(session, uuid.UUID(candidate_id_str), "rejected")

        await update_workflow_run(
            session,
            uuid.UUID(run_id_str),
            status="completed",
            current_node="output",
            progress=result.progress,
            screening_passed=result.screening_passed,
            screening_reason=result.screening_reason,
            completed_at=datetime.now(),
        )
        await session.commit()


@router.post("/run", response_model=WorkflowRunResponse, status_code=202)
async def run_workflow_endpoint(
    body: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Trigger a product evaluation workflow for a candidate."""
    candidate = await get_candidate(session, uuid.UUID(body.candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    run = await create_workflow_run(
        session,
        candidate_id=candidate.id,
        status="running",
        current_node="normalize",
        started_at=datetime.now(),
    )
    run_id = str(run.id)
    await session.commit()

    background_tasks.add_task(_run_workflow_background, run_id, body.candidate_id)

    return WorkflowRunResponse(run_id=run_id, candidate_id=body.candidate_id, status="running")


@router.get("/{run_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status_endpoint(
    run_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get the current status of a workflow run."""
    run = await get_workflow_run(session, uuid.UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return WorkflowStatusResponse(
        run_id=str(run.id),
        status=run.status,
        current_node=run.current_node,
        progress=run.progress if isinstance(run.progress, list) else [],
        error_message=run.error_message,
    )
