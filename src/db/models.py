"""SQLAlchemy ORM models — portable across SQLite and PostgreSQL.

List-valued columns are stored as JSON so the same schema runs on SQLite
(the default local database) without dialect-specific array types.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    source_country: Mapped[str] = mapped_column(String(3), nullable=False)
    target_country: Mapped[str] = mapped_column(String(3), nullable=False)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    moq: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketTrend(Base):
    __tablename__ = "market_trends"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False)
    period_month: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    search_volume: Mapped[int | None] = mapped_column(Integer)
    growth_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    avg_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    review_count: Mapped[int | None] = mapped_column(Integer)
    top_keywords: Mapped[list | None] = mapped_column(JSON)
    influencer_mentions: Mapped[int] = mapped_column(Integer, default=0)
    creator_sellers: Mapped[int] = mapped_column(Integer, default=0)
    avg_monthly_revenue_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    source_country: Mapped[str] = mapped_column(String(3), nullable=False)
    unit_price_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moq: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    freight_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    freight_cost_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    port_of_origin: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    target_country: Mapped[str] = mapped_column(String(3), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    required_certs: Mapped[list | None] = mapped_column(JSON)
    banned_substances: Mapped[list | None] = mapped_column(JSON)
    import_duty_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Trademark(Base):
    __tablename__ = "trademarks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit: Mapped[str | None] = mapped_column(String(50))
    source_tool: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    fetch_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    validity_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.80"))
    raw_response: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecisionCard(Base):
    __tablename__ = "decision_cards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    candidate_name: Mapped[str | None] = mapped_column(String(500))
    verdict: Mapped[str] = mapped_column(String(10), nullable=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    unit_economics: Mapped[dict | None] = mapped_column(JSON)
    evidence_summary: Mapped[dict | None] = mapped_column(JSON)
    risk_flags: Mapped[dict | None] = mapped_column(JSON)
    watch_reasons: Mapped[dict | None] = mapped_column(JSON)
    gatekeeper_report: Mapped[dict | None] = mapped_column(JSON)
    tool_trace: Mapped[list | None] = mapped_column(JSON)
    reviewed_by: Mapped[str] = mapped_column(String(50), default="decision_review_agent")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    current_node: Mapped[str | None] = mapped_column(String(50))
    progress: Mapped[list | None] = mapped_column(JSON, default=list)
    screening_passed: Mapped[bool | None] = mapped_column(Boolean)
    screening_reason: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
