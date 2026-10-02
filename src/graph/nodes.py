"""Workflow nodes — each function corresponds to a step in the evaluation pipeline."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from src.agents.compliance_risk import run_compliance_risk_agent
from src.agents.decision_review import run_decision_review_agent
from src.agents.supply_cost import run_supply_cost_agent
from src.agents.trend_demand import run_trend_demand_agent
from src.decision.card import DecisionCard
from src.evidence.gatekeeper import gatekeep
from src.evidence.merge import merge_evidence
from src.evidence.models import EvidenceItem
from src.graph.state import WorkflowState
from src.llm.factory import get_llm
from src.screening.funnel import screen_candidate
from src.screening.normalize import normalize_candidate


def normalize_node(state: WorkflowState) -> dict:
    """Node: Normalize candidate fields."""
    raw = state.get("candidate_raw", {})
    normalized = normalize_candidate(raw)
    return {
        "candidate_normalized": normalized,
        "current_node": "normalize",
        "progress": [{"node": "normalize", "status": "completed", "ts": datetime.now().isoformat()}],
    }


def screen_node(state: WorkflowState) -> dict:
    """Node: Apply quick screening funnel."""
    normalized = state.get("candidate_normalized")
    if normalized is None:
        return {
            "screening_passed": False,
            "screening_reason": "No normalized candidate data",
            "current_node": "screen",
            "progress": [{"node": "screen", "status": "failed", "ts": datetime.now().isoformat()}],
        }

    result = screen_candidate(normalized)
    return {
        "screening_passed": result.passed,
        "screening_reason": result.reject_reason or "Passed all screening criteria",
        "current_node": "screen",
        "progress": [{
            "node": "screen",
            "status": "passed" if result.passed else "rejected",
            "ts": datetime.now().isoformat(),
        }],
    }


def fan_out_node(state: WorkflowState) -> dict:
    """Node: Fan-out placeholder — signals parallel evidence collection start."""
    return {
        "current_node": "fan_out",
        "progress": [{"node": "fan_out", "status": "started", "ts": datetime.now().isoformat()}],
    }


async def collect_evidence_trend_node(state: WorkflowState) -> dict:
    """Node: Run Trend & Demand evidence agent."""
    llm = get_llm()
    run_id = state.get("run_id", uuid.uuid4().hex)
    candidate_id = state.get("candidate_id", "")
    candidate_raw = state.get("candidate_raw", {})

    try:
        items = await run_trend_demand_agent(llm, run_id, candidate_id, candidate_raw)
    except Exception as e:
        items = []
        error = str(e)
        return {
            "evidence_items": items,
            "evidence_errors": [f"trend_demand: {error}"],
            "current_node": "collect_evidence_trend",
            "progress": [{"node": "collect_evidence_trend", "status": "error", "ts": datetime.now().isoformat()}],
        }

    return {
        "evidence_items": items,
        "evidence_errors": [],
        "current_node": "collect_evidence_trend",
        "progress": [{"node": "collect_evidence_trend", "status": "completed", "ts": datetime.now().isoformat()}],
    }


async def collect_evidence_supply_node(state: WorkflowState) -> dict:
    """Node: Run Supply & Cost evidence agent."""
    llm = get_llm()
    run_id = state.get("run_id", uuid.uuid4().hex)
    candidate_id = state.get("candidate_id", "")
    candidate_raw = state.get("candidate_raw", {})

    try:
        items = await run_supply_cost_agent(llm, run_id, candidate_id, candidate_raw)
    except Exception as e:
        items = []
        return {
            "evidence_items": items,
            "evidence_errors": [f"supply_cost: {str(e)}"],
            "current_node": "collect_evidence_supply",
            "progress": [{"node": "collect_evidence_supply", "status": "error", "ts": datetime.now().isoformat()}],
        }

    return {
        "evidence_items": items,
        "evidence_errors": [],
        "current_node": "collect_evidence_supply",
        "progress": [{"node": "collect_evidence_supply", "status": "completed", "ts": datetime.now().isoformat()}],
    }


async def collect_evidence_compliance_node(state: WorkflowState) -> dict:
    """Node: Run Compliance & Risk evidence agent."""
    llm = get_llm()
    run_id = state.get("run_id", uuid.uuid4().hex)
    candidate_id = state.get("candidate_id", "")
    candidate_raw = state.get("candidate_raw", {})

    try:
        items = await run_compliance_risk_agent(llm, run_id, candidate_id, candidate_raw)
    except Exception as e:
        items = []
        return {
            "evidence_items": items,
            "evidence_errors": [f"compliance_risk: {str(e)}"],
            "current_node": "collect_evidence_compliance",
            "progress": [{"node": "collect_evidence_compliance", "status": "error", "ts": datetime.now().isoformat()}],
        }

    return {
        "evidence_items": items,
        "evidence_errors": [],
        "current_node": "collect_evidence_compliance",
        "progress": [{"node": "collect_evidence_compliance", "status": "completed", "ts": datetime.now().isoformat()}],
    }


def gatekeep_node(state: WorkflowState) -> dict:
    """Node: Evidence gatekeeping — validate, strip unsourced, check confidence."""
    evidence_items = state.get("evidence_items", [])

    # Merge evidence from 3 agents (dedup)
    trend = [e for e in evidence_items if e.agent_type.value == "trend_demand"]
    supply = [e for e in evidence_items if e.agent_type.value == "supply_cost"]
    compliance = [e for e in evidence_items if e.agent_type.value == "compliance_risk"]
    merged = merge_evidence(trend, supply, compliance)

    # Gatekeep
    gated, report = gatekeep(merged)

    return {
        "gated_evidence": gated,
        "gatekeeper_report": report.model_dump(),
        "current_node": "gatekeep",
        "progress": [{
            "node": "gatekeep",
            "status": "completed",
            "ts": datetime.now().isoformat(),
            "detail": f"valid={report.valid_items}, stripped={report.stripped_items}",
        }],
    }


async def review_node(state: WorkflowState) -> dict:
    """Node: Decision Review — cross-examination, scoring, verdict."""
    llm = get_llm()
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
    except Exception as e:
        # Fallback: minimal decision card
        decision_card = DecisionCard(
            run_id=run_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            verdict="no_go",
            verdict_reason=f"Review failed: {str(e)[:100]}",
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
            "ts": datetime.now().isoformat(),
            "verdict": decision_card.verdict,
        }],
    }


def output_node(state: WorkflowState) -> dict:
    """Node: Persist decision card (side effects)."""
    # In a full implementation, this would write to DB.
    # For the demo, the decision card is already in state.
    return {
        "current_node": "output",
        "progress": [{"node": "output", "status": "completed", "ts": datetime.now().isoformat()}],
    }
