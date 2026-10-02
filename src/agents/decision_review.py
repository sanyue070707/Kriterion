"""Decision Review Agent — cross-examination, scoring, and verdict."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.decision_review import SYSTEM_PROMPT
from src.config.platform_profiles import get_profile
from src.decision.card import DecisionCard, LLDecisionOutput
from src.decision.scorer import score_all_dimensions
from src.decision.verdict import compute_verdict
from src.evidence.gatekeeper import gatekeep
from src.evidence.models import EvidenceItem


async def run_decision_review_agent(
    llm: BaseChatModel,
    run_id: str,
    candidate_id: str,
    candidate_name: str,
    candidate_info: dict[str, Any],
    gated_evidence: list[EvidenceItem],
) -> DecisionCard:
    """Run the Decision Review agent.

    This agent:
    1. Groups evidence by dimension for scoring
    2. Computes 7-dimension scores using deterministic logic
    3. Computes verdict using deterministic rules
    4. Optionally uses LLM for cross-examination narrative
    5. Assembles the DecisionCard
    """
    # 1. Group evidence by dimension for scoring
    evidence_by_dim: dict[str, list[EvidenceItem]] = {}
    for item in gated_evidence:
        dim = item.dimension.value
        evidence_by_dim.setdefault(dim, []).append(item)

    # 2. Compute scores
    score_result = score_all_dimensions(evidence_by_dim)

    # 3. Compute verdict
    platform = candidate_info.get("platform", "tiktok_shop")
    try:
        profile = get_profile(platform)
        min_margin = profile.min_viable_margin_pct
    except (KeyError, ValueError):
        min_margin = 15.0

    verdict_result = compute_verdict(
        overall_score=score_result.overall_score,
        scores=score_result.scores_dict,
        evidence_items=gated_evidence,
        min_margin_pct=min_margin,
    )

    # 4. Build evidence summary from LLM cross-examination (optional)
    evidence_summary = _build_evidence_summary(gated_evidence)
    risk_flags = _extract_risk_flags(gated_evidence)
    watch_reasons = _extract_watch_reasons(verdict_result.verdict, score_result.scores_dict, gated_evidence)

    # 5. Compute unit economics if we have cost evidence
    unit_economics = _compute_unit_economics_from_evidence(candidate_info, gated_evidence)

    return DecisionCard(
        run_id=run_id,
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        verdict=verdict_result.verdict,
        verdict_reason=verdict_result.reason,
        scores=score_result.scores_dict,
        overall_score=score_result.overall_score,
        unit_economics=unit_economics,
        evidence_summary=evidence_summary,
        risk_flags=risk_flags,
        watch_reasons=watch_reasons,
        reviewed_by="decision_review_agent",
        decided_at=datetime.now(),
    )


def _build_evidence_summary(evidence: list[EvidenceItem]) -> dict:
    """Build a human-readable evidence summary grouped by agent."""
    summary: dict[str, list[str]] = {}
    for item in evidence:
        agent = item.agent_type.value
        summary.setdefault(agent, []).append(f"{item.dimension.value}: {item.claim}")
    return summary


def _extract_risk_flags(evidence: list[EvidenceItem]) -> dict:
    """Extract critical risk flags from evidence."""
    flags = {}
    for item in evidence:
        if item.dimension.value in ("compliance_block", "trademark_risk") and item.value and float(item.value) > 0:
            flags[item.claim[:80]] = "critical"
        elif item.dimension.value == "compliance_warn" and item.value and float(item.value) > 0:
            flags[item.claim[:80]] = "warning"
    return flags


def _extract_watch_reasons(
    verdict: str,
    scores: dict[str, float],
    evidence: list[EvidenceItem],
) -> dict:
    """Extract watch reasons if verdict is 'watch'."""
    if verdict != "watch":
        return {}

    reasons = {}
    for dim, score in scores.items():
        if score < 5.0:
            reasons[dim] = f"Score {score} below average"

    # Check for low-confidence evidence
    low_conf = [e for e in evidence if e.confidence < Decimal("0.60")]
    if low_conf:
        reasons["low_confidence"] = f"{len(low_conf)} evidence items with confidence < 0.60"

    return reasons


def _compute_unit_economics_from_evidence(
    candidate_info: dict[str, Any],
    evidence: list[EvidenceItem],
) -> dict | None:
    """Try to compute unit economics from evidence data."""
    try:
        from src.decision.unit_economics import calculate_unit_economics

        platform = candidate_info.get("platform", "tiktok_shop")
        category = candidate_info.get("category", "beauty")
        retail = float(candidate_info.get("price_usd", 0))

        # Extract from evidence
        product_cost = 0.0
        freight_cost = 0.0
        creator_commission = None
        import_duty = 0.0

        for item in evidence:
            if item.dimension.value == "product_cost" and item.value:
                product_cost = float(item.value)
            elif item.dimension.value == "freight_cost" and item.value:
                weight = float(candidate_info.get("weight_kg", 1))
                freight_cost = float(item.value) * weight
            elif item.dimension.value == "creator_commission" and item.value:
                creator_commission = float(item.value)
            elif item.dimension.value == "import_duty" and item.value:
                import_duty = float(item.value)

        if retail > 0 and product_cost > 0:
            ue = calculate_unit_economics(
                platform=platform,
                category=category,
                retail_price_usd=retail,
                product_cost_usd=product_cost,
                freight_cost_usd=freight_cost,
                creator_commission_pct=creator_commission,
                import_duty_pct=import_duty,
            )
            return ue.to_dict()
    except Exception:
        pass

    return None
