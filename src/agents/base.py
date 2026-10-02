"""Shared evidence-collection entry point for the three agents.

Evidence is produced by running a declarative plan (see `plan.py` / `plans.py`).
Every number therefore carries the tool that produced it and a source
reference, which is what makes the evidence ledger meaningful.

The tool-selection strategy is isolated here: to drive it with a model instead
of a fixed checklist, replace the body below with a tool-calling loop
(bind_tools -> tool calls -> observe -> repeat). The rest of the pipeline is
agnostic, since either returns `(evidence_items, tool_calls)`.
"""

from __future__ import annotations

from typing import Any

from src.agents.plan import PlanContext, ToolCallRecord, run_plan
from src.agents.plans import build_plan
from src.evidence.models import AgentType, EvidenceItem


async def run_evidence_agent(
    agent_type: AgentType,
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> tuple[list[EvidenceItem], list[ToolCallRecord]]:
    """Run an agent's evidence plan.

    Returns the evidence it collected plus the tool-call trace.
    """
    context = PlanContext(
        agent_type=agent_type,
        run_id=run_id,
        candidate_id=candidate_id,
        candidate=candidate_info,
    )
    items = await run_plan(build_plan(agent_type), context)
    return items, context.tool_calls
