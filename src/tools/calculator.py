"""Calculator tools — unit economics and margin calculations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from langchain_core.tools import tool


@tool
def margin_calculator(
    retail_price: float,
    total_cost: float,
) -> dict:
    """Calculate gross and net margin from retail price and total cost.

    Args:
        retail_price: Selling price in USD
        total_cost: Total cost (product + freight + commissions + all fees) in USD

    Returns margin percentages and profit.
    """
    retail = Decimal(str(retail_price))
    cost = Decimal(str(total_cost))
    profit = retail - cost
    gross_margin = (profit / retail * 100) if retail > 0 else Decimal("0")

    return {
        "retail_price_usd": retail_price,
        "total_cost_usd": total_cost,
        "profit_usd": float(profit.quantize(Decimal("0.01"))),
        "margin_pct": float(gross_margin.quantize(Decimal("0.01"))),
        "is_profitable": profit > 0,
        "fetch_time": datetime.now().isoformat(),
    }


@tool
def break_even_calculator(
    fixed_cost_monthly: float,
    profit_per_unit: float,
) -> dict:
    """Calculate monthly break-even units.

    Args:
        fixed_cost_monthly: Monthly fixed costs in USD
        profit_per_unit: Net profit per unit in USD

    Returns break-even units and days to break even at various sales rates.
    """
    if profit_per_unit <= 0:
        return {
            "break_even_units": float("inf"),
            "message": "Cannot break even — no profit per unit",
        }

    units = fixed_cost_monthly / profit_per_unit

    return {
        "fixed_cost_monthly_usd": fixed_cost_monthly,
        "profit_per_unit_usd": profit_per_unit,
        "break_even_units": round(units, 1),
        "at_10_units_day": round(units / 10, 1) if units > 0 else 0,
        "at_50_units_day": round(units / 50, 1) if units > 0 else 0,
        "at_100_units_day": round(units / 100, 1) if units > 0 else 0,
        "fetch_time": datetime.now().isoformat(),
    }
