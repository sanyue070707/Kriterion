"""Trend & Demand Evidence Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from src.agents.base import run_evidence_agent
from src.agents.prompts.trend_demand import SYSTEM_PROMPT
from src.evidence.models import AgentType, EvidenceItem
from src.tools.registry import get_tools_for_agent


async def run_trend_demand_agent(
    llm: BaseChatModel,
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> list[EvidenceItem]:
    """Run the Trend & Demand evidence agent."""
    tools = get_tools_for_agent("trend_demand")
    return await run_evidence_agent(
        llm=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        agent_type=AgentType.TREND_DEMAND,
        run_id=run_id,
        candidate_id=candidate_id,
        candidate_info=candidate_info,
    )
