"""Evaluation service — the single entry point that runs the workflow.

Both the HTTP background task and the CLI call this, so a candidate is evaluated
by exactly the same code path regardless of how it was triggered.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.decision.card import DecisionCard
from src.evidence.models import EvidenceItem
from src.graph.workflow import get_workflow


@dataclass
class EvalResult:
    run_id: str
    candidate_id: str
    candidate_name: str
    verdict: str
    decision_card: DecisionCard | None
    gated_evidence: list[EvidenceItem] = field(default_factory=list)
    gatekeeper_report: dict = field(default_factory=dict)
    tool_trace: list[dict] = field(default_factory=list)
    screening_passed: bool | None = None
    screening_reason: str = ""
    evidence_errors: list[str] = field(default_factory=list)
    progress: list[dict] = field(default_factory=list)


def candidate_to_raw(candidate: Any) -> dict:
    """Serialize a Candidate ORM row into the workflow's raw candidate dict."""
    return {
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


async def run_evaluation(candidate_raw: dict, run_id: str | None = None) -> EvalResult:
    """Run the full evaluation workflow for a candidate and collect its result."""
    run_id = run_id or uuid.uuid4().hex
    workflow = get_workflow()

    initial_state = {
        "run_id": run_id,
        "candidate_id": str(candidate_raw.get("id", "")),
        "candidate_raw": candidate_raw,
        "evidence_items": [],
        "evidence_errors": [],
        "tool_trace": [],
        "progress": [],
    }
    result = await workflow.ainvoke(initial_state)

    card: DecisionCard | None = result.get("decision_card")
    return EvalResult(
        run_id=run_id,
        candidate_id=str(candidate_raw.get("id", "")),
        candidate_name=candidate_raw.get("name", "Unknown"),
        verdict=(card.verdict if card else "no_go"),
        decision_card=card,
        gated_evidence=result.get("gated_evidence", []),
        gatekeeper_report=result.get("gatekeeper_report", {}),
        tool_trace=result.get("tool_trace", []),
        screening_passed=result.get("screening_passed"),
        screening_reason=result.get("screening_reason", ""),
        evidence_errors=result.get("evidence_errors", []),
        progress=result.get("progress", []),
    )
