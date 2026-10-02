"""Workflow API endpoints — trigger and monitor evaluations."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import WorkflowRunRequest, WorkflowRunResponse, WorkflowStatusResponse
from src.db.connection import get_session
from src.db.models import WorkflowRun
from src.db.repository import (
    create_decision_card,
    create_evidence_item,
    create_workflow_run,
    get_candidate,
    get_workflow_run,
    update_candidate_status,
    update_workflow_run,
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


async def _run_workflow_background(run_id_str: str, candidate_id_str: str) -> None:
    """Execute the evaluation workflow in the background and persist results."""
    from src.graph.workflow import get_workflow

    # Get candidate data from DB
    from src.db.connection import async_session_factory

    async with async_session_factory() as session:
        candidate = await get_candidate(session, uuid.UUID(candidate_id_str))
        if not candidate:
            return

        candidate_raw = {
            "id": str(candidate.id),
            "name": candidate.name,
            "category": candidate.category,
            "subcategory": candidate.subcategory,
            "platform": candidate.platform,
            "source_country": candidate.source_country,
            "target_country": candidate.target_country,
            "price_usd": float(candidate.price_usd) if candidate.price_usd else None,
            "moq": candidate.moq,
            "weight_kg": float(candidate.weight_kg) if candidate.weight_kg else None,
            "metadata": candidate.metadata_,
        }

    # Run workflow
    workflow = get_workflow()
    initial_state = {
        "run_id": run_id_str,
        "candidate_id": candidate_id_str,
        "candidate_raw": candidate_raw,
        "evidence_items": [],
        "evidence_errors": [],
        "progress": [],
    }

    try:
        result = await workflow.ainvoke(initial_state)
    except Exception as e:
        # Mark workflow as failed
        async with async_session_factory() as session:
            await update_workflow_run(session, uuid.UUID(run_id_str), status="failed", error_message=str(e)[:500])
            await session.commit()
        return

    # Persist results
    async with async_session_factory() as session:
        # Update workflow status
        await update_workflow_run(
            session,
            uuid.UUID(run_id_str),
            status="completed",
            current_node="output",
            completed_at=datetime.now(),
        )

        # Persist evidence items
        for item in result.get("gated_evidence", []):
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

        # Persist decision card
        card = result.get("decision_card")
        if card:
            await create_decision_card(
                session,
                run_id=uuid.UUID(run_id_str),
                candidate_id=uuid.UUID(candidate_id_str),
                verdict=card.verdict,
                scores=card.scores,
                overall_score=card.overall_score,
                unit_economics=card.unit_economics,
                evidence_summary=card.evidence_summary,
                risk_flags=card.risk_flags,
                watch_reasons=card.watch_reasons,
            )

            # Update candidate status
            new_status = "decided" if card.verdict in ("go", "no_go") else "watch"
            await update_candidate_status(session, uuid.UUID(candidate_id_str), new_status)

        await session.commit()


@router.post("/run", response_model=WorkflowRunResponse, status_code=202)
async def run_workflow_endpoint(
    body: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Trigger a product evaluation workflow for a candidate."""
    # Validate candidate exists
    candidate = await get_candidate(session, uuid.UUID(body.candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Create workflow run
    run = await create_workflow_run(
        session,
        candidate_id=candidate.id,
        status="running",
        current_node="normalize",
        started_at=datetime.now(),
    )
    run_id = str(run.id)
    await session.commit()

    # Schedule background execution
    background_tasks.add_task(_run_workflow_background, run_id, body.candidate_id)

    return WorkflowRunResponse(
        run_id=run_id,
        candidate_id=body.candidate_id,
        status="running",
    )


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
