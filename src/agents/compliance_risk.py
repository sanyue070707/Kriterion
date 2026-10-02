"""Compliance & Risk Evidence Agent."""

from __future__ import annotations

from typing import Any

from src.agents.base import run_evidence_agent
from src.agents.plan import ToolCallRecord
from src.evidence.models import AgentType, EvidenceItem


async def run_compliance_risk_agent(
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> tuple[list[EvidenceItem], list[ToolCallRecord]]:
    """Collect compliance evidence (trademarks, certifications, policy blocks)."""
    return await run_evidence_agent(AgentType.COMPLIANCE_RISK, run_id, candidate_id, candidate_info)
