"""Tests for the evidence-plan executor and dimension mapping (no DB needed)."""

from decimal import Decimal

from langchain_core.tools import tool

from src.agents.plan import PlanContext, Rule, SkipStep, run_plan
from src.decision.scorer import DIMENSION_EVIDENCE, bucket_evidence
from src.evidence.models import AgentType, EvidenceItem
from src.evidence.models import EvidenceDimension as Dim


@tool
def double_tool(x: int) -> dict:
    """Return double the input (a stand-in business tool)."""
    return {"value": x * 2, "source_url": f"calc://double?x={x}", "fetch_time": "2025-06-01T00:00:00"}


@tool
def boom_tool(x: int) -> dict:
    """Always raises, to exercise degradation."""
    raise RuntimeError("source unavailable")


def _context() -> PlanContext:
    return PlanContext(
        agent_type=AgentType.SUPPLY_COST, run_id="run-1", candidate_id="cand-1", candidate={"x": 21}
    )


class TestPlanExecutor:
    async def test_records_tool_call_and_provenance(self):
        plan = [Rule(
            tool=double_tool,
            primary_dimension=Dim.PRODUCT_COST,
            args=lambda ctx: {"x": 21},
            emit=lambda result, ctx: [{
                "dimension": Dim.PRODUCT_COST, "claim": "doubled", "value": result["value"], "unit": "USD",
            }],
        )]
        ctx = _context()
        items = await run_plan(plan, ctx)

        assert len(ctx.tool_calls) == 1
        call = ctx.tool_calls[0]
        assert call.tool == "double_tool" and call.ok and not call.skipped

        assert len(items) == 1
        item = items[0]
        assert item.value == Decimal("42")
        assert item.source_tool == "double_tool"          # real tool name, not a hardcoded label
        assert item.source_url == "calc://double?x=21"    # real provenance
        assert item.validity_until is not None            # TTL applied

    async def test_tool_failure_degrades_to_gap_evidence(self):
        plan = [Rule(
            tool=boom_tool,
            primary_dimension=Dim.PRODUCT_COST,
            args=lambda ctx: {"x": 1},
            emit=lambda result, ctx: [],
        )]
        ctx = _context()
        items = await run_plan(plan, ctx)

        assert ctx.tool_calls[0].ok is False
        assert len(items) == 1
        assert items[0].value is None
        assert items[0].confidence == Decimal("0.20")
        assert items[0].raw_response.get("degraded") is True

    async def test_skip_step_is_recorded(self):
        def _raise(ctx):
            raise SkipStep("missing upstream input")

        plan = [Rule(
            tool=double_tool,
            primary_dimension=Dim.NET_MARGIN,
            args=_raise,
            emit=lambda result, ctx: [],
        )]
        ctx = _context()
        items = await run_plan(plan, ctx)

        assert ctx.tool_calls[0].skipped is True
        # A non-optional skipped step surfaces as a low-confidence gap.
        assert len(items) == 1 and items[0].value is None

    async def test_optional_skip_produces_nothing(self):
        def _raise(ctx):
            raise SkipStep("optional")

        plan = [Rule(
            tool=double_tool,
            primary_dimension=Dim.POLICY_REFERENCE,
            args=_raise,
            emit=lambda result, ctx: [],
            optional=True,
        )]
        ctx = _context()
        items = await run_plan(plan, ctx)

        assert ctx.tool_calls[0].skipped is True
        assert items == []


def _item(dimension: Dim, value: Decimal | None = Decimal("1")) -> EvidenceItem:
    return EvidenceItem(
        run_id="r", candidate_id="c", agent_type=AgentType.SUPPLY_COST,
        dimension=dimension, claim="x", value=value, source_tool="t", confidence=Decimal("0.8"),
    )


class TestDimensionMapping:
    def test_heavy_dimensions_receive_evidence(self):
        """cost_margin and compliance_risk must not be starved."""
        items = [
            _item(Dim.NET_MARGIN, Decimal("30")),
            _item(Dim.GROSS_MARGIN, Decimal("40")),
            _item(Dim.COMPLIANCE_BLOCK, Decimal("1")),
            _item(Dim.TRADEMARK_RISK, Decimal("0")),
        ]
        buckets = bucket_evidence(items)
        assert len(buckets["cost_margin"]) == 2
        assert len(buckets["compliance_risk"]) == 2

    def test_context_dimensions_are_not_scored(self):
        """Policy references / precedents inform the ledger but do not score."""
        items = [_item(Dim.POLICY_REFERENCE, None), _item(Dim.HISTORICAL_PRECEDENT, None)]
        assert all(not bucket for bucket in bucket_evidence(items).values())

    def test_every_scoring_dimension_is_mapped(self):
        from src.decision.scorer import ALL_DIMENSIONS
        assert set(DIMENSION_EVIDENCE) == set(ALL_DIMENSIONS)
