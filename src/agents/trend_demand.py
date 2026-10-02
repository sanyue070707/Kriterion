"""Trend & Demand Evidence Agent."""

from __future__ import annotations

from typing import Any

from src.agents.base import run_evidence_agent
from src.agents.plan import ToolCallRecord
from src.evidence.models import AgentType, EvidenceItem


async def run_trend_demand_agent(
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> tuple[list[EvidenceItem], list[ToolCallRecord]]:
    """Collect market-demand evidence (search volume, growth, competition)."""
    return await run_evidence_agent(AgentType.TREND_DEMAND, run_id, candidate_id, candidate_info)
