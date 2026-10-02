"""Tests for evidence ledger."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem
from src.evidence.ledger import EvidenceLedger


def _make_item(
    agent_type: AgentType = AgentType.TREND_DEMAND,
    dimension: EvidenceDimension = EvidenceDimension.MARKET_DEMAND,
    claim: str = "Test claim",
    value: Decimal | None = None,
    confidence: Decimal = Decimal("0.80"),
    source_tool: str = "test_tool",
    validity_until: datetime | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        run_id="run-001",
        candidate_id="cand-001",
        agent_type=agent_type,
        dimension=dimension,
        claim=claim,
        value=value,
        source_tool=source_tool,
        confidence=confidence,
        validity_until=validity_until,
    )


class TestEvidenceLedger:
    def test_append(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        item = _make_item()
        ledger.append(item)
        assert len(ledger) == 1

    def test_append_wrong_run_id(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        item = _make_item()
        item.run_id = "run-002"
        try:
            ledger.append(item)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_items_by_agent(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        ledger.append(_make_item(agent_type=AgentType.TREND_DEMAND))
        ledger.append(_make_item(agent_type=AgentType.SUPPLY_COST))
        ledger.append(_make_item(agent_type=AgentType.TREND_DEMAND))
        assert len(ledger.items_by_agent(AgentType.TREND_DEMAND)) == 2
        assert len(ledger.items_by_agent(AgentType.SUPPLY_COST)) == 1
        assert len(ledger.items_by_agent(AgentType.COMPLIANCE_RISK)) == 0

    def test_validate_all_good(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        ledger.append(_make_item(confidence=Decimal("0.80")))
        issues = ledger.validate()
        assert len(issues) == 0

    def test_validate_no_source(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        ledger.append(_make_item(source_tool=""))
        issues = ledger.validate()
        assert len(issues) > 0
        assert "no source" in issues[0].lower()

    def test_validate_low_confidence(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        ledger.append(_make_item(confidence=Decimal("0.30")))
        issues = ledger.validate()
        assert len(issues) > 0
        assert "low confidence" in issues[0].lower()

    def test_validate_expired(self):
        ledger = EvidenceLedger(run_id="run-001", candidate_id="cand-001")
        ledger.append(_make_item(validity_until=datetime.now() - timedelta(hours=1)))
        issues = ledger.validate()
        assert len(issues) > 0
        assert "expired" in issues[0].lower()
