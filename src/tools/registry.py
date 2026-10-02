"""Tool registry — map agent names to their tool sets."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from src.tools.calculator import break_even_calculator, margin_calculator
from src.tools.compliance import check_certifications, check_policy_compliance, check_trademark
from src.tools.market_trend import get_category_growth, get_influencer_data, search_trends
from src.tools.rag_search import hybrid_search
from src.tools.supply_cost import (
    calculate_freight,
    calculate_unit_economics_tool,
    get_platform_commission,
    get_supplier_quotes,
)


def get_tools_for_agent(agent_name: str) -> list[BaseTool]:
    """Return the set of tools for a specific evidence agent."""
    if agent_name == "trend_demand":
        return [search_trends, get_category_growth, get_influencer_data, hybrid_search]

    if agent_name == "supply_cost":
        return [
            get_supplier_quotes,
            calculate_freight,
            get_platform_commission,
            calculate_unit_economics_tool,
            margin_calculator,
            break_even_calculator,
            hybrid_search,
        ]

    if agent_name == "compliance_risk":
        return [check_trademark, check_certifications, check_policy_compliance, hybrid_search]

    # Decision review agent doesn't need tools (it's a structured-output chain)
    if agent_name == "decision_review":
        return []

    raise ValueError(f"Unknown agent: {agent_name}")
