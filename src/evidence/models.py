"""Evidence models — data structures for the evidence ledger mechanism."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    TREND_DEMAND = "trend_demand"
    SUPPLY_COST = "supply_cost"
    COMPLIANCE_RISK = "compliance_risk"


class EvidenceDimension(str, Enum):
    # Trend & Demand
    MARKET_DEMAND = "market_demand"
    COMPETITION = "competition"
    TREND_MOMENTUM = "trend_momentum"
    INFLUENCER_ACTIVITY = "influencer_activity"
    # Supply & Cost
    PRODUCT_COST = "product_cost"
    FREIGHT_COST = "freight_cost"
    PLATFORM_COMMISSION = "platform_commission"
    CREATOR_COMMISSION = "creator_commission"
    GROSS_MARGIN = "gross_margin"
    NET_MARGIN = "net_margin"
    SUPPLY_STABILITY = "supply_stability"
    # Compliance & Risk
    TRADEMARK_RISK = "trademark_risk"
    CERTIFICATION_GAP = "certification_gap"
    COMPLIANCE_BLOCK = "compliance_block"
    COMPLIANCE_WARN = "compliance_warn"
    IMPORT_DUTY = "import_duty"
    # Cross-cutting
    RETURN_RATE = "return_rate"
    # Retrieval context — shown in the evidence ledger, not scored
    POLICY_REFERENCE = "policy_reference"
    HISTORICAL_PRECEDENT = "historical_precedent"


class EvidenceItem(BaseModel):
    """A single evidence item — one data-backed claim from an agent."""

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    run_id: str
    candidate_id: str
    agent_type: AgentType
    dimension: EvidenceDimension
    claim: str  # Human-readable assertion
    value: Decimal | None = None  # Numeric value if applicable
    unit: str | None = None  # "USD", "%", "units", etc.
    source_tool: str  # Tool that produced this evidence
    source_url: str | None = None  # Original data reference
    fetch_time: datetime = Field(default_factory=datetime.now)
    validity_until: datetime | None = None  # Data staleness deadline
    confidence: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)  # 0.00-1.00
    raw_response: dict | None = None  # Original tool response for audit

    @property
    def is_expired(self) -> bool:
        """Check if the evidence data has expired."""
        if self.validity_until is None:
            return False
        return datetime.now() > self.validity_until

    @property
    def has_source(self) -> bool:
        """Check if this evidence item has a valid source attribution."""
        return bool(self.source_tool)


class GatekeeperReport(BaseModel):
    """Report from the evidence gatekeeper."""

    total_items: int
    valid_items: int
    stripped_items: int
    low_confidence_items: int
    expired_items: int
    stripped_reasons: list[str] = []
    confidence_summary: dict[str, float] = {}  # agent_type → avg confidence
