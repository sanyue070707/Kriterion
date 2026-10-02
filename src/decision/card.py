"""Decision Card — structured output model for the final decision."""

from __future__ import annotations

from datetime import datetime
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
# The numbers on a decision card are computed deterministically (scorer +
# verdict). The model only renders the *narrative* around them, and is
# constrained to this schema so its output can be validated. With a real model
# this is used via `llm.with_structured_output(LLNarrativeOutput)`.

class LLNarrativeOutput(BaseModel):
    """Narrative fields the LLM fills; the decision numbers are ignored here."""

    verdict_reason: str = Field(description="One-sentence, grounded reason for the verdict")
    evidence_summary: dict = Field(default_factory=dict, description="Key evidence highlights")
    watch_reasons: dict = Field(default_factory=dict, description="If verdict=watch, what to watch for")
    narrative: str = Field(default="", description="Short analyst narrative over the computed scores")
