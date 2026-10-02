"""Supply & Cost Evidence Agent."""

from __future__ import annotations

from typing import Any

from src.agents.base import run_evidence_agent
from src.agents.plan import ToolCallRecord
from src.evidence.models import AgentType, EvidenceItem


async def run_supply_cost_agent(
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> tuple[list[EvidenceItem], list[ToolCallRecord]]:
    """Collect supply/cost evidence (supplier quotes, freight, commissions, margin)."""
    return await run_evidence_agent(AgentType.SUPPLY_COST, run_id, candidate_id, candidate_info)
