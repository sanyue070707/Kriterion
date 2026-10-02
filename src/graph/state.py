"""WorkflowState — TypedDict state definition for the LangGraph workflow."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from operator import add

from src.evidence.models import EvidenceItem
from src.decision.card import DecisionCard
from src.screening.normalize import NormalizedCandidate


class WorkflowState(TypedDict, total=False):
    """State that flows through the evaluation workflow.

    Key design:
    - evidence_items uses Annotated[list, add] so parallel agents
      can each append their results and LangGraph auto-merges by concatenation.
    - progress also uses add for concurrent progress updates.
    """

    # ── Candidate input ──
    candidate_id: str
    candidate_raw: dict
    candidate_normalized: NormalizedCandidate

    # ── Screening ──
    screening_passed: bool
    screening_reason: str

    # ── Evidence collection (3 agents each append) ──
    evidence_items: Annotated[list[EvidenceItem], add]
    evidence_errors: Annotated[list[str], add]

    # ── Gatekeeping ──
    gated_evidence: list[EvidenceItem]
    gatekeeper_report: dict

    # ── Decision ──
    decision_card: DecisionCard
    verdict: Literal["go", "watch", "no_go"]

    # ── Workflow metadata ──
    run_id: str
    current_node: str
    progress: Annotated[list[dict], add]
