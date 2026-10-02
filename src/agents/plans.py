"""The three evidence checklists.

Each plan is an ordered list of `Rule`s naming the business tools an agent
consults, in what order, and how each result becomes evidence. Order matters
where a later step depends on an earlier one's output (e.g. unit economics
needs a supplier quote).
"""

from __future__ import annotations

from src.agents.plan import PlanContext, Rule, SkipStep
from src.evidence.models import AgentType
from src.evidence.models import EvidenceDimension as Dim
from src.tools.compliance import check_certifications, check_policy_compliance, check_trademark
from src.tools.market_trend import get_category_growth, get_influencer_data, search_trends
from src.tools.provenance import confidence_from_n
from src.tools.rag_search import hybrid_search
from src.tools.supply_cost import (
    calculate_freight,
    calculate_unit_economics_tool,
    get_platform_commission,
    get_supplier_quotes,
)

CONF_LOW = 0.2


# ── Trend & Demand ──────────────────────────────────────────────────────────


def _trend_search_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if not result.get("found"):
        return [{"dimension": Dim.MARKET_DEMAND, "claim": result.get("message", "No trend data"),
                 "value": None, "confidence": CONF_LOW}]
    return [{
        "dimension": Dim.MARKET_DEMAND,
        "claim": f"Average search volume {result['avg_search_volume']:,}/month ({result['trend_direction']})",
        "value": result["avg_search_volume"],
        "unit": "searches/month",
        "confidence": confidence_from_n(result.get("data_points", 0)),
    }]


def _growth_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if not result.get("found"):
        return []
    return [{
        "dimension": Dim.TREND_MOMENTUM,
        "claim": f"Category growing {result['avg_growth_rate_pct']}% YoY ({result['momentum']})",
        "value": result["avg_growth_rate_pct"],
        "unit": "%",
        "confidence": confidence_from_n(result.get("months_available", 0), full_at=6, floor=0.6),
    }]


def _influencer_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if not result.get("found"):
        return []
    return [
        {
            "dimension": Dim.INFLUENCER_ACTIVITY,
            "claim": f"{result['avg_influencer_mentions']} influencer mentions/month on average",
            "value": result["avg_influencer_mentions"],
            "unit": "mentions",
            "confidence": confidence_from_n(result.get("max_influencer_mentions", 0), full_at=50, floor=0.6),
        },
        {
            "dimension": Dim.COMPETITION,
            "claim": f"{result['avg_creator_sellers']} active creator-sellers (avg per month)",
            "value": result["avg_creator_sellers"],
            "unit": "sellers",
            "confidence": confidence_from_n(result.get("max_creator_sellers", 0), full_at=20, floor=0.6),
        },
    ]


def _trend_rag_emit(result: dict, ctx: PlanContext) -> list[dict]:
    return [
        {
            "dimension": Dim.HISTORICAL_PRECEDENT,
            "claim": f"Similar past case: {hit['text'][:150]}",
            "value": None,
            "confidence": 0.6,
        }
        for hit in result.get("results", [])[:2]
    ]


TREND_PLAN: list[Rule] = [
    Rule(
        tool=search_trends,
        primary_dimension=Dim.MARKET_DEMAND,
        args=lambda ctx: {"category": ctx.candidate["category"], "country": ctx.candidate["target_country"]},
        emit=_trend_search_emit,
    ),
    Rule(
        tool=get_category_growth,
        primary_dimension=Dim.TREND_MOMENTUM,
        args=lambda ctx: {
            "category": ctx.candidate["category"],
            "platform": ctx.candidate["platform"],
            "country": ctx.candidate["target_country"],
        },
        emit=_growth_emit,
    ),
    Rule(
        tool=get_influencer_data,
        primary_dimension=Dim.INFLUENCER_ACTIVITY,
        args=lambda ctx: {"category": ctx.candidate["category"], "country": ctx.candidate["target_country"]},
        emit=_influencer_emit,
    ),
    Rule(
        tool=hybrid_search,
        primary_dimension=Dim.HISTORICAL_PRECEDENT,
        args=lambda ctx: {
            "query": (
                f"{ctx.candidate['category']} {ctx.candidate['platform']} "
                f"{ctx.candidate['target_country']} verdict"
            ),
            "collection": "historical_decisions",
            "top_k": 2,
        },
        emit=_trend_rag_emit,
        optional=True,
    ),
]


# ── Supply & Cost ───────────────────────────────────────────────────────────


def _quotes_apply(result: dict, ctx: PlanContext) -> None:
    if not result.get("found"):
        return
    quotes = result.get("top_quotes", [])
    if quotes:
        best = min(quotes, key=lambda q: q["unit_price_usd"])
        ctx.facts["best_quote"] = best
        ctx.facts["distinct_suppliers"] = len({q["supplier_id"] for q in quotes})
        ctx.facts["freight_mode"] = best.get("freight_mode") or "sea"


def _quotes_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if not result.get("found"):
        return [{"dimension": Dim.PRODUCT_COST, "claim": result.get("message", "No supplier quotes"),
                 "value": None, "confidence": CONF_LOW}]
    distinct = ctx.facts.get("distinct_suppliers", 0)
    return [
        {
            "dimension": Dim.PRODUCT_COST,
            "claim": f"Lowest supplier unit price ${result['min_price_usd']} (avg ${result['avg_price_usd']})",
            "value": result["min_price_usd"],
            "unit": "USD",
            "confidence": confidence_from_n(result.get("supplier_count", 0), full_at=20),
        },
        {
            "dimension": Dim.SUPPLY_STABILITY,
            "claim": f"{distinct} distinct suppliers available for {result['category']}",
            "value": distinct,
            "unit": "suppliers",
            "confidence": confidence_from_n(distinct, full_at=8),
        },
    ]


def _commission_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if not result.get("found"):
        return []
    payloads = [{
        "dimension": Dim.PLATFORM_COMMISSION,
        "claim": (
            f"Platform commission {result['commission_pct']}% + "
            f"{result['payment_processing_pct']}% payment processing"
        ),
        "value": result["commission_pct"],
        "unit": "%",
        "confidence": 0.85,
    }]
    if result.get("typical_return_rate_pct") is not None:
        payloads.append({
            "dimension": Dim.RETURN_RATE,
            "claim": f"Typical return rate {result['typical_return_rate_pct']}% (max {result['max_return_rate_pct']}%)",
            "value": result["typical_return_rate_pct"],
            "unit": "%",
            "confidence": 0.7,
        })
    return payloads


def _freight_args(ctx: PlanContext) -> dict:
    weight = ctx.candidate.get("weight_kg")
    if weight is None:
        raise SkipStep("candidate weight unknown")
    return {
        "weight_kg": float(weight),
        "source_country": ctx.candidate["source_country"],
        "target_country": ctx.candidate["target_country"],
        "mode": ctx.facts.get("freight_mode", "sea"),
    }


def _freight_apply(result: dict, ctx: PlanContext) -> None:
    ctx.facts["freight_cost_usd"] = result.get("total_cost_usd", 0.0)


def _freight_emit(result: dict, ctx: PlanContext) -> list[dict]:
    return [{
        "dimension": Dim.FREIGHT_COST,
        "claim": f"Head freight ({result['mode']}) ${result['rate_per_kg']}/kg -> ${result['total_cost_usd']} per unit",
        "value": result["total_cost_usd"],
        "unit": "USD",
        "confidence": 0.8,
    }]


def _unit_econ_args(ctx: PlanContext) -> dict:
    best = ctx.facts.get("best_quote")
    retail = ctx.candidate.get("price_usd")
    if not best or retail is None:
        raise SkipStep("no supplier quote / retail price — cannot compute unit economics")
    return {
        "platform": ctx.candidate["platform"],
        "category": ctx.candidate["category"],
        "retail_price_usd": float(retail),
        "product_cost_usd": float(best["unit_price_usd"]),
        "freight_cost_usd": float(ctx.facts.get("freight_cost_usd", 0.0)),
        "import_duty_pct": float(ctx.facts.get("import_duty_pct", 0.0)),
    }


def _unit_econ_apply(result: dict, ctx: PlanContext) -> None:
    if "error" not in result:
        ctx.facts["unit_economics"] = result


def _unit_econ_emit(result: dict, ctx: PlanContext) -> list[dict]:
    if "error" in result:
        return []
    return [
        {
            "dimension": Dim.GROSS_MARGIN,
            "claim": f"Gross margin {result['gross_margin_pct']}% (${result['gross_profit']}/unit)",
            "value": result["gross_margin_pct"],
            "unit": "%",
            "confidence": 0.8,
        },
        {
            "dimension": Dim.NET_MARGIN,
            "claim": f"Net margin {result['net_margin_pct']}% after all platform/creator/return costs",
            "value": result["net_margin_pct"],
            "unit": "%",
            "confidence": 0.75,
        },
    ]


SUPPLY_PLAN: list[Rule] = [
    Rule(
        tool=get_supplier_quotes,
        primary_dimension=Dim.PRODUCT_COST,
        args=lambda ctx: {"category": ctx.candidate["category"], "source_country": ctx.candidate["source_country"]},
        emit=_quotes_emit,
        apply=_quotes_apply,
    ),
    Rule(
        tool=get_platform_commission,
        primary_dimension=Dim.PLATFORM_COMMISSION,
        args=lambda ctx: {"platform": ctx.candidate["platform"], "category": ctx.candidate["category"]},
        emit=_commission_emit,
    ),
    Rule(
        tool=calculate_freight,
        primary_dimension=Dim.FREIGHT_COST,
        args=_freight_args,
        emit=_freight_emit,
        apply=_freight_apply,
    ),
    Rule(
        tool=calculate_unit_economics_tool,
        primary_dimension=Dim.NET_MARGIN,
        args=_unit_econ_args,
        emit=_unit_econ_emit,
        apply=_unit_econ_apply,
    ),
]


# ── Compliance & Risk ───────────────────────────────────────────────────────


def _trademark_emit(result: dict, ctx: PlanContext) -> list[dict]:
    conflicts = result.get("conflicts_found", 0)
    if conflicts:
        names = ", ".join(c["trademark_name"] for c in result.get("conflicts", [])[:3])
        claim = f"{conflicts} trademark conflict(s) found: {names}"
    else:
        claim = f"No trademark conflicts among {result.get('trademarks_checked', 0)} marks checked"
    return [{
        "dimension": Dim.TRADEMARK_RISK,
        "claim": claim,
        "value": conflicts,
        "unit": "conflicts",
        "confidence": confidence_from_n(result.get("trademarks_checked", 0), full_at=20),
    }]


def _certs_emit(result: dict, ctx: PlanContext) -> list[dict]:
    n = result.get("certification_count", 0)
    certs = ", ".join(result.get("required_certifications", [])[:4])
    return [{
        "dimension": Dim.CERTIFICATION_GAP,
        "claim": f"{n} certification(s) required: {certs}" if n else "No specific certifications required",
        "value": n,
        "unit": "certs",
        "confidence": confidence_from_n(result.get("policies_checked", 0), full_at=20),
    }]


def _policy_apply(result: dict, ctx: PlanContext) -> None:
    duties = [
        entry["import_duty_pct"]
        for entry in (result.get("blocks", []) + result.get("warnings", []) + result.get("info", []))
        if entry.get("import_duty_pct") is not None
    ]
    ctx.facts["import_duty_pct"] = max(duties) if duties else 0.0


def _policy_emit(result: dict, ctx: PlanContext) -> list[dict]:
    payloads: list[dict] = []
    block_count = result.get("block_count", 0)
    if block_count:
        first = result["blocks"][0]["description"]
        payloads.append({
            "dimension": Dim.COMPLIANCE_BLOCK,
            "claim": f"{block_count} blocking rule(s), e.g. {first}",
            "value": block_count,
            "unit": "blocks",
            "confidence": 0.85,
        })
    warn_count = result.get("warning_count", 0)
    if warn_count:
        payloads.append({
            "dimension": Dim.COMPLIANCE_WARN,
            "claim": f"{warn_count} policy warning(s) require attention",
            "value": warn_count,
            "unit": "warnings",
            "confidence": 0.75,
        })
    duty = ctx.facts.get("import_duty_pct")
    if duty:
        payloads.append({
            "dimension": Dim.IMPORT_DUTY,
            "claim": f"Import duty up to {duty}%",
            "value": duty,
            "unit": "%",
            "confidence": 0.8,
        })
    return payloads


def _policy_rag_emit(result: dict, ctx: PlanContext) -> list[dict]:
    return [
        {
            "dimension": Dim.POLICY_REFERENCE,
            "claim": f"Applicable policy: {hit['text'][:150]}",
            "value": None,
            "confidence": 0.6,
        }
        for hit in result.get("results", [])[:2]
    ]


COMPLIANCE_PLAN: list[Rule] = [
    Rule(
        tool=check_trademark,
        primary_dimension=Dim.TRADEMARK_RISK,
        args=lambda ctx: {
            "product_name": ctx.candidate["name"],
            "category": ctx.candidate["category"],
            "target_country": ctx.candidate["target_country"],
        },
        emit=_trademark_emit,
    ),
    Rule(
        tool=check_certifications,
        primary_dimension=Dim.CERTIFICATION_GAP,
        args=lambda ctx: {
            "category": ctx.candidate["category"],
            "source_country": ctx.candidate["source_country"],
            "target_country": ctx.candidate["target_country"],
        },
        emit=_certs_emit,
    ),
    Rule(
        tool=check_policy_compliance,
        primary_dimension=Dim.COMPLIANCE_BLOCK,
        args=lambda ctx: {
            "product_name": ctx.candidate["name"],
            "category": ctx.candidate["category"],
            "target_country": ctx.candidate["target_country"],
        },
        emit=_policy_emit,
        apply=_policy_apply,
    ),
    Rule(
        tool=hybrid_search,
        primary_dimension=Dim.POLICY_REFERENCE,
        args=lambda ctx: {
            "query": f"{ctx.candidate['category']} {ctx.candidate['target_country']} certification prohibition duty",
            "collection": "compliance_policies",
            "top_k": 2,
            "filters": {"target_country": ctx.candidate["target_country"], "category": ctx.candidate["category"]},
        },
        emit=_policy_rag_emit,
        optional=True,
    ),
]


PLANS: dict[AgentType, list[Rule]] = {
    AgentType.TREND_DEMAND: TREND_PLAN,
    AgentType.SUPPLY_COST: SUPPLY_PLAN,
    AgentType.COMPLIANCE_RISK: COMPLIANCE_PLAN,
}


def build_plan(agent_type: AgentType) -> list[Rule]:
    """Return the evidence checklist for an agent type."""
    return PLANS[agent_type]
