"""Tests for evidence gatekeeper."""

from datetime import datetime, timedelta
from decimal import Decimal

from src.evidence.gatekeeper import gatekeep
from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem


def _make_item(
    source_tool: str = "test_tool",
    confidence: Decimal = Decimal("0.80"),
    validity_until: datetime | None = None,
    claim: str = "Test claim",
    agent_type: AgentType = AgentType.TREND_DEMAND,
) -> EvidenceItem:
    return EvidenceItem(
        run_id="run-001",
        candidate_id="cand-001",
        agent_type=agent_type,
        dimension=EvidenceDimension.MARKET_DEMAND,
        claim=claim,
        value=Decimal("100"),
        source_tool=source_tool,
        confidence=confidence,
        validity_until=validity_until,
    )


class TestGatekeeper:
    def test_all_valid(self):
        items = [_make_item(), _make_item(), _make_item()]
        gated, report = gatekeep(items)
        assert len(gated) == 3
        assert report.valid_items == 3
        assert report.stripped_items == 0

    def test_strips_no_source(self):
        items = [_make_item(source_tool=""), _make_item(source_tool="good_tool")]
        gated, report = gatekeep(items)
        assert len(gated) == 1
        assert report.stripped_items == 1

    def test_flags_low_confidence(self):
        items = [_make_item(confidence=Decimal("0.30"))]
        gated, report = gatekeep(items)
        # Not stripped, but flagged
        assert len(gated) == 1
        assert report.low_confidence_items == 1

    def test_strips_expired(self):
        expired_time = datetime.now() - timedelta(hours=1)
        items = [_make_item(validity_until=expired_time)]
        gated, report = gatekeep(items)
        assert len(gated) == 0
        assert report.expired_items == 1

    def test_confidence_summary(self):
        items = [
            _make_item(agent_type=AgentType.TREND_DEMAND, confidence=Decimal("0.90")),
            _make_item(agent_type=AgentType.TREND_DEMAND, confidence=Decimal("0.70")),
            _make_item(agent_type=AgentType.SUPPLY_COST, confidence=Decimal("0.80")),
        ]
        gated, report = gatekeep(items)
        assert "trend_demand" in report.confidence_summary
        assert "supply_cost" in report.confidence_summary
        assert abs(report.confidence_summary["trend_demand"] - 0.80) < 0.01
