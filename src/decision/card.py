"""Decision Card — structured output model for the final decision."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class DecisionCard(BaseModel):
    """Structured decision card — the final output of the evaluation workflow."""

    run_id: str
    candidate_id: str
    candidate_name: str

    # Verdict
    verdict: Literal["go", "watch", "no_go"]
    verdict_reason: str

    # Seven-dimension scores
    scores: dict[str, float] = Field(
        description="Scores for each of the 7 dimensions (0-10)",
        examples=[{
            "market_demand": 7.5,
            "competition": 6.0,
            "cost_margin": 8.2,
            "compliance_risk": 9.0,
            "supply_stability": 6.5,
            "trend_momentum": 7.0,
            "return_rate": 8.0,
        }],
    )
    overall_score: float = Field(ge=0, le=10, description="Weighted composite score")

    # Unit economics
    unit_economics: dict | None = Field(None, description="Platform P&L breakdown")

    # Evidence summary
    evidence_summary: dict = Field(
        default_factory=dict,
        description="Grouped evidence highlights by agent",
    )

    # Risk flags
    risk_flags: dict = Field(
        default_factory=dict,
        description="Critical risks identified",
    )

    # Watch reasons (only if verdict=watch)
    watch_reasons: dict = Field(
        default_factory=dict,
        description="What to watch for if verdict is watch",
    )

    # Metadata
    reviewed_by: str = "decision_review_agent"
    decided_at: datetime = Field(default_factory=datetime.now)

    def to_api_response(self) -> dict:
        """Convert to API-friendly dict."""
        return {
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "verdict": self.verdict,
            "verdict_reason": self.verdict_reason,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "unit_economics": self.unit_economics,
            "evidence_summary": self.evidence_summary,
            "risk_flags": self.risk_flags,
            "watch_reasons": self.watch_reasons,
            "reviewed_by": self.reviewed_by,
            "decided_at": self.decided_at.isoformat(),
        }


# ── Structured Output Schema for LLM ──
# This is used with `with_structured_output` to force the LLM to produce
# a valid DecisionCard. We define a simplified version for the LLM to fill.

class LLDecisionOutput(BaseModel):
    """Schema for LLM structured output — the LLM fills this, then we build DecisionCard."""

    verdict: Literal["go", "watch", "no_go"] = Field(description="Go / Watch / No-Go verdict")
    verdict_reason: str = Field(description="One-sentence reason for the verdict")
    scores: dict[str, float] = Field(
        description="Score for each dimension (0-10): market_demand, competition, cost_margin, compliance_risk, supply_stability, trend_momentum, return_rate",
    )
    overall_score: float = Field(ge=0, le=10, description="Weighted overall score 0-10")
    evidence_summary: dict = Field(default_factory=dict, description="Key evidence highlights grouped by agent")
    risk_flags: dict = Field(default_factory=dict, description="Critical risks: {risk_name: severity}")
    watch_reasons: dict = Field(default_factory=dict, description="If verdict=watch, what to watch for")
