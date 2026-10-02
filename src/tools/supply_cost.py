"""Supply & cost tools — for Supply & Cost Agent."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from langchain_core.tools import tool

from src.config.platform_profiles import get_commission_rate, get_profile
from src.db.connection import async_session_factory
from src.db.repository import query_supplier_quotes
from src.decision.unit_economics import calculate_unit_economics


@tool
async def get_supplier_quotes(category: str, source_country: str) -> dict:
    """Get available supplier quotes for a category from a source country.

    Returns list of suppliers with unit prices, MOQ, and lead times.
    """
    async with async_session_factory() as session:
        results = await query_supplier_quotes(session, category, source_country)

    if not results:
        return {"found": False, "message": f"No suppliers for {category} from {source_country}"}

    quotes = []
    for r in results[:10]:  # Top 10
        quotes.append({
            "supplier_id": r.supplier_id,
            "unit_price_usd": float(r.unit_price_usd),
            "moq": r.moq,
            "lead_time_days": r.lead_time_days,
            "freight_mode": r.freight_mode,
            "freight_cost_per_kg": float(r.freight_cost_per_kg) if r.freight_cost_per_kg else None,
        })

    prices = [float(r.unit_price_usd) for r in results]
    return {
        "found": True,
        "category": category,
        "source_country": source_country,
        "supplier_count": len(results),
        "min_price_usd": round(min(prices), 2),
        "avg_price_usd": round(sum(prices) / len(prices), 2),
        "max_price_usd": round(max(prices), 2),
        "top_quotes": quotes,
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def calculate_freight(
    weight_kg: float,
    source_country: str,
    target_country: str,
    mode: str = "sea",
) -> dict:
    """Calculate head-cost freight for shipping.

    Args:
        weight_kg: Product weight in kg
        source_country: Origin country code
        target_country: Destination country code
        mode: 'sea', 'air', or 'express'

    Returns cost per kg and total cost.
    """
    # Freight rates (approximate, per kg)
    rates = {
        "sea": {"CN": 1.5, "KR": 2.0, "JP": 2.2, "TH": 1.8},
        "air": {"CN": 5.5, "KR": 6.0, "JP": 6.5, "TH": 5.0},
        "express": {"CN": 10.0, "KR": 11.0, "JP": 12.0, "TH": 9.0},
    }
    days = {"sea": (30, 45), "air": (5, 10), "express": (3, 5)}

    rate_per_kg = rates.get(mode, rates["sea"]).get(source_country, 2.0)
    min_days, max_days = days.get(mode, (30, 45))
    total = round(rate_per_kg * weight_kg, 2)

    return {
        "weight_kg": weight_kg,
        "source_country": source_country,
        "target_country": target_country,
        "mode": mode,
        "rate_per_kg": rate_per_kg,
        "total_cost_usd": total,
        "transit_days": f"{min_days}-{max_days}",
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def get_platform_commission(platform: str, category: str) -> dict:
    """Get commission rate and payment processing fee for a platform and category."""
    try:
        profile = get_profile(platform)
        commission_pct = get_commission_rate(platform, category)
        return {
            "found": True,
            "platform": platform,
            "category": category,
            "commission_pct": commission_pct,
            "payment_processing_pct": profile.payment_processing_pct,
            "creator_commission_range": f"{profile.creator_commission_min_pct}-{profile.creator_commission_max_pct}%",
            "fetch_time": datetime.now().isoformat(),
        }
    except (KeyError, ValueError) as e:
        return {"found": False, "message": str(e)}


@tool
async def calculate_unit_economics_tool(
    platform: str,
    category: str,
    retail_price_usd: float,
    product_cost_usd: float,
    freight_cost_usd: float,
    creator_commission_pct: float | None = None,
    import_duty_pct: float = 0.0,
    return_rate_pct: float | None = None,
) -> dict:
    """Calculate full unit economics P&L for a product.

    Returns gross margin, net margin, and cost breakdown.
    """
    try:
        ue = calculate_unit_economics(
            platform=platform,
            category=category,
            retail_price_usd=retail_price_usd,
            product_cost_usd=product_cost_usd,
            freight_cost_usd=freight_cost_usd,
            creator_commission_pct=creator_commission_pct,
            import_duty_pct=import_duty_pct,
            return_rate_pct=return_rate_pct,
        )
        return {
            **ue.to_dict(),
            "fetch_time": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}
