"""Tests for decision scorer and verdict."""

from decimal import Decimal

from src.decision.scorer import score_all_dimensions, score_dimension
from src.decision.verdict import compute_verdict
from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem


def _make_evidence(
    dimension: EvidenceDimension = EvidenceDimension.MARKET_DEMAND,
    value: Decimal = Decimal("100"),
    confidence: Decimal = Decimal("0.80"),
) -> EvidenceItem:
    return EvidenceItem(
        run_id="run-001",
        candidate_id="cand-001",
        agent_type=AgentType.TREND_DEMAND,
        dimension=dimension,
        claim="Test",
        value=value,
        source_tool="test",
        confidence=confidence,
    )


class TestScorer:
    def test_score_dimension_no_evidence(self):
        result = score_dimension("market_demand", [])
        assert result.score == 5.0  # neutral
        assert result.evidence_count == 0

    def test_score_market_demand(self):
        items = [_make_evidence(EvidenceDimension.MARKET_DEMAND, Decimal("100000"))]
        result = score_dimension("market_demand", items)
        assert 0 <= result.score <= 10
        assert result.evidence_count == 1

    def test_score_all_dimensions(self):
        evidence = {
            "market_demand": [_make_evidence(EvidenceDimension.MARKET_DEMAND, Decimal("100000"))],
            "competition": [_make_evidence(EvidenceDimension.COMPETITION, Decimal("5"))],
            "cost_margin": [_make_evidence(EvidenceDimension.GROSS_MARGIN, Decimal("30"))],
            "compliance_risk": [_make_evidence(EvidenceDimension.COMPLIANCE_WARN, Decimal("1"))],
            "supply_stability": [_make_evidence(EvidenceDimension.SUPPLY_STABILITY, Decimal("7"))],
            "trend_momentum": [_make_evidence(EvidenceDimension.TREND_MOMENTUM, Decimal("20"))],
            "return_rate": [_make_evidence(EvidenceDimension.RETURN_RATE, Decimal("8"))],
        }
        result = score_all_dimensions(evidence)
        assert 0 <= result.overall_score <= 10
        assert len(result.scores_dict) == 7
        assert all(0 <= v <= 10 for v in result.scores_dict.values())


class TestVerdict:
    def test_verdict_go(self):
        scores = {
            "market_demand": 8, "competition": 7, "cost_margin": 8,
            "compliance_risk": 9, "supply_stability": 7, "trend_momentum": 8, "return_rate": 8,
        }
        result = compute_verdict(7.5, scores, [])
        assert result.verdict == "go"

    def test_verdict_no_go_low_score(self):
        scores = {
            "market_demand": 2, "competition": 2, "cost_margin": 2,
            "compliance_risk": 3, "supply_stability": 2, "trend_momentum": 2, "return_rate": 3,
        }
        result = compute_verdict(3.5, scores, [])
        assert result.verdict == "no_go"

    def test_verdict_no_go_compliance_block(self):
        block_evidence = [EvidenceItem(
            run_id="r", candidate_id="c", agent_type=AgentType.COMPLIANCE_RISK,
            dimension=EvidenceDimension.COMPLIANCE_BLOCK, claim="Blocked",
            value=Decimal("1"), source_tool="test", confidence=Decimal("0.90"),
        )]
        scores = {
            "market_demand": 8, "competition": 7, "cost_margin": 8,
            "compliance_risk": 3, "supply_stability": 7, "trend_momentum": 8, "return_rate": 8,
        }
        result = compute_verdict(7.0, scores, block_evidence)
        assert result.verdict == "no_go"

    def test_verdict_watch(self):
        scores = {
            "market_demand": 5, "competition": 5, "cost_margin": 5,
            "compliance_risk": 6, "supply_stability": 5, "trend_momentum": 5, "return_rate": 6,
        }
        result = compute_verdict(5.3, scores, [])
        assert result.verdict == "watch"
