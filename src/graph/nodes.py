"""Workflow nodes — each function is one step of the evaluation pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime

from src.agents.compliance_risk import run_compliance_risk_agent
from src.agents.decision_review import run_decision_review_agent
from src.agents.supply_cost import run_supply_cost_agent
from src.agents.trend_demand import run_trend_demand_agent
from src.decision.card import DecisionCard
from src.evidence.gatekeeper import gatekeep
from src.evidence.merge import merge_evidence
from src.graph.state import WorkflowState
from src.llm.factory import get_llm
from src.screening.funnel import screen_candidate
from src.screening.normalize import normalize_candidate


def _now() -> str:
    return datetime.now().isoformat()


def normalize_node(state: WorkflowState) -> dict:
    """Node: normalize candidate fields."""
    normalized = normalize_candidate(state.get("candidate_raw", {}))
    return {
        "candidate_normalized": normalized,
        "current_node": "normalize",
        "progress": [{"node": "normalize", "status": "completed", "ts": _now()}],
    }


def screen_node(state: WorkflowState) -> dict:
    """Node: apply the quick screening funnel."""
    normalized = state.get("candidate_normalized")
    if normalized is None:
        return {
            "screening_passed": False,
            "screening_reason": "No normalized candidate data",
            "current_node": "screen",
            "progress": [{"node": "screen", "status": "failed", "ts": _now()}],
        }

    result = screen_candidate(normalized)
    return {
        "screening_passed": result.passed,
        "screening_reason": result.reject_reason or "Passed all screening criteria",
        "current_node": "screen",
        "progress": [{
            "node": "screen",
            "status": "passed" if result.passed else "rejected",
            "ts": _now(),
        }],
    }


def fan_out_node(state: WorkflowState) -> dict:
    """Node: fan out — signals parallel evidence collection start."""
    return {
        "current_node": "fan_out",
        "progress": [{"node": "fan_out", "status": "started", "ts": _now()}],
    }


async def _collect(node_name, agent_runner, state: WorkflowState) -> dict:
    """Shared body for the three evidence nodes."""
    run_id = state.get("run_id", uuid.uuid4().hex)
    candidate_id = state.get("candidate_id", "")
    candidate_raw = state.get("candidate_raw", {})

    # These nodes run concurrently, so they only write reducer-backed state
    # keys; node identity is carried in the `progress` list.
    try:
        items, tool_calls = await agent_runner(run_id, candidate_id, candidate_raw)
    except Exception as exc:  # noqa: BLE001 - an agent failure must not abort the run
        return {
            "evidence_items": [],
            "tool_trace": [],
            "evidence_errors": [f"{node_name}: {str(exc)[:200]}"],
            "progress": [{"node": node_name, "status": "error", "ts": _now()}],
        }

    return {
        "evidence_items": items,
        "tool_trace": [call.to_dict() for call in tool_calls],
        "evidence_errors": [],
        "progress": [{
            "node": node_name,
            "status": "completed",
            "ts": _now(),
            "detail": f"{len(items)} evidence items / {len(tool_calls)} tool calls",
        }],
    }


async def collect_evidence_trend_node(state: WorkflowState) -> dict:
    """Node: run the Trend & Demand evidence agent."""
    return await _collect("collect_evidence_trend", run_trend_demand_agent, state)


async def collect_evidence_supply_node(state: WorkflowState) -> dict:
    """Node: run the Supply & Cost evidence agent."""
    return await _collect("collect_evidence_supply", run_supply_cost_agent, state)


async def collect_evidence_compliance_node(state: WorkflowState) -> dict:
    """Node: run the Compliance & Risk evidence agent."""
    return await _collect("collect_evidence_compliance", run_compliance_risk_agent, state)


def gatekeep_node(state: WorkflowState) -> dict:
    """Node: merge the three agents' evidence and gatekeep it."""
    evidence_items = state.get("evidence_items", [])

    trend = [e for e in evidence_items if e.agent_type.value == "trend_demand"]
    supply = [e for e in evidence_items if e.agent_type.value == "supply_cost"]
    compliance = [e for e in evidence_items if e.agent_type.value == "compliance_risk"]
    merged = merge_evidence(trend, supply, compliance)

    gated, report = gatekeep(merged)

    return {
        "gated_evidence": gated,
        "gatekeeper_report": report.model_dump(),
        "current_node": "gatekeep",
        "progress": [{
            "node": "gatekeep",
            "status": "completed",
            "ts": _now(),
            "detail": f"valid={report.valid_items}, stripped={report.stripped_items}",
        }],
    }


async def review_node(state: WorkflowState) -> dict:
    """Node: decision review — cross-examination, scoring, verdict."""
    llm = get_llm(role="decision_review")
    run_id = state.get("run_id", uuid.uuid4().hex)
    candidate_id = state.get("candidate_id", "")
    candidate_raw = state.get("candidate_raw", {})
    candidate_name = candidate_raw.get("name", "Unknown")
    gated_evidence = state.get("gated_evidence", [])

    try:
        decision_card = await run_decision_review_agent(
            llm=llm,
            run_id=run_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            candidate_info=candidate_raw,
            gated_evidence=gated_evidence,
        )
    except Exception as exc:  # noqa: BLE001 - fall back to a minimal card
        decision_card = DecisionCard(
            run_id=run_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            verdict="no_go",
            verdict_reason=f"Review failed: {str(exc)[:100]}",
            scores={},
            overall_score=0.0,
        )

    return {
        "decision_card": decision_card,
        "verdict": decision_card.verdict,
        "current_node": "review",
        "progress": [{
            "node": "review",
            "status": "completed",
            "ts": _now(),
            "verdict": decision_card.verdict,
        }],
    }


def output_node(state: WorkflowState) -> dict:
    """Node: finalize the decision card (persistence happens in the service layer)."""
    return {
        "current_node": "output",
        "progress": [{"node": "output", "status": "completed", "ts": _now()}],
    }
