"""Decision Review Agent — cross-examination, scoring, and verdict.

Design: the *numbers* (seven-dimension scores, verdict, unit economics) are
computed deterministically from gatekept evidence — the decision must not
depend on model whim. The LLM is used only to render a grounded narrative over
those numbers, constrained to `LLNarrativeOutput`; if that call fails, the
deterministic reason is kept.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.decision_review import SYSTEM_PROMPT
from src.config.platform_profiles import get_profile
from src.decision.card import DecisionCard, LLNarrativeOutput
from src.decision.scorer import bucket_evidence, score_all_dimensions
from src.decision.verdict import compute_verdict
from src.evidence.models import EvidenceItem

MAX_HIGHLIGHTS = 8


async def run_decision_review_agent(
    llm: BaseChatModel,
    run_id: str,
    candidate_id: str,
    candidate_name: str,
    candidate_info: dict[str, Any],
    gated_evidence: list[EvidenceItem],
) -> DecisionCard:
    """Score, adjudicate, and narrate a decision from gatekept evidence."""
    # 1. Group evidence into the seven scoring dimensions and score.
    score_result = score_all_dimensions(bucket_evidence(gated_evidence))

    # 2. Deterministic verdict.
    platform = candidate_info.get("platform", "tiktok_shop")
    try:
        min_margin = get_profile(platform).min_viable_margin_pct
    except (KeyError, ValueError):
        min_margin = 15.0

    verdict_result = compute_verdict(
        overall_score=score_result.overall_score,
        scores=score_result.scores_dict,
        evidence_items=gated_evidence,
        min_margin_pct=min_margin,
    )

    risk_flags = _extract_risk_flags(gated_evidence)
    watch_reasons = _extract_watch_reasons(verdict_result.verdict, score_result.scores_dict, gated_evidence)
    unit_economics = _compute_unit_economics_from_evidence(candidate_info, gated_evidence)
    evidence_summary = _build_evidence_summary(gated_evidence)

    # 3. Grounded narrative (LLM renders; numbers come from above).
    verdict_reason = verdict_result.reason
    highlights = [e.claim for e in gated_evidence][:MAX_HIGHLIGHTS]
    facts = {
        "verdict": verdict_result.verdict,
        "verdict_reason": verdict_result.reason,
        "overall_score": score_result.overall_score,
        "scores": score_result.scores_dict,
        "risk_flags": risk_flags,
        "watch_reasons": watch_reasons,
        "evidence_highlights": highlights,
    }
    narrative = await _render_narrative(llm, facts)
    if narrative is not None:
        if narrative.verdict_reason:
            verdict_reason = narrative.verdict_reason
        if narrative.narrative:
            evidence_summary["narrative"] = narrative.narrative

    return DecisionCard(
        run_id=run_id,
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        verdict=verdict_result.verdict,
        verdict_reason=verdict_reason,
        scores=score_result.scores_dict,
        overall_score=score_result.overall_score,
        unit_economics=unit_economics,
        evidence_summary=evidence_summary,
        risk_flags=risk_flags,
        watch_reasons=watch_reasons,
        reviewed_by="decision_review_agent",
        decided_at=datetime.now(),
    )


async def _render_narrative(llm: BaseChatModel, facts: dict) -> LLNarrativeOutput | None:
    """Ask the model to narrate the facts; return None on any failure."""
    try:
        payload = HumanMessage(content=json.dumps({"role": "decision_review", "facts": facts}, default=str))
        response = await llm.ainvoke([SystemMessage(content=SYSTEM_PROMPT), payload])
        return LLNarrativeOutput.model_validate_json(response.content)
    except Exception:  # noqa: BLE001 - narrative is best-effort
        return None


def _build_evidence_summary(evidence: list[EvidenceItem]) -> dict:
    """Human-readable evidence highlights grouped by agent."""
    by_agent: dict[str, list[str]] = {}
    for item in evidence:
        by_agent.setdefault(item.agent_type.value, []).append(f"{item.dimension.value}: {item.claim}")
    return {"by_agent": by_agent}


def _extract_risk_flags(evidence: list[EvidenceItem]) -> dict:
    """Critical risks from blocking compliance / trademark evidence."""
    flags: dict[str, str] = {}
    for item in evidence:
        if item.value is None:
            continue
        if item.dimension.value in ("compliance_block", "trademark_risk") and float(item.value) > 0:
            flags[item.claim[:80]] = "critical"
        elif item.dimension.value == "compliance_warn" and float(item.value) > 0:
            flags[item.claim[:80]] = "warning"
    return flags


def _extract_watch_reasons(verdict: str, scores: dict[str, float], evidence: list[EvidenceItem]) -> dict:
    """Reasons to keep watching, when the verdict is 'watch'."""
    if verdict != "watch":
        return {}

    reasons: dict[str, str] = {}
    for dim, score in scores.items():
        if score < 5.0:
            reasons[dim] = f"Score {score} below average"
    low_confidence = [e for e in evidence if e.confidence < Decimal("0.60")]
    if low_confidence:
        reasons["low_confidence"] = f"{len(low_confidence)} evidence items with confidence < 0.60"
    return reasons


def _compute_unit_economics_from_evidence(candidate_info: dict[str, Any], evidence: list[EvidenceItem]) -> dict | None:
    """Recompute the per-unit P&L from gatekept evidence (authoritative)."""
    try:
        from src.decision.unit_economics import calculate_unit_economics

        platform = candidate_info.get("platform", "tiktok_shop")
        category = candidate_info.get("category", "beauty")
        retail = float(candidate_info.get("price_usd") or 0)

        product_cost = 0.0
        freight_cost = 0.0
        creator_commission = None
        import_duty = 0.0

        for item in evidence:
            if item.value is None:
                continue
            if item.dimension.value == "product_cost":
                # Prefer the lowest product cost reported.
                product_cost = float(item.value) if not product_cost else min(product_cost, float(item.value))
            elif item.dimension.value == "freight_cost":
                freight_cost = float(item.value)
            elif item.dimension.value == "creator_commission":
                creator_commission = float(item.value)
            elif item.dimension.value == "import_duty":
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
    except Exception:  # noqa: BLE001 - unit economics is best-effort
        pass

    return None
