"""Market trend tools — for Trend & Demand Agent."""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from src.db.connection import async_session_factory
from src.db.repository import query_market_trends
from src.tools.provenance import dataset_url


@tool
async def search_trends(category: str, country: str, period: str = "last_6_months") -> dict:
    """Search market trend data for a product category in a target country.

    Returns search volume, growth rate, and trend direction for recent months.
    """
    async with async_session_factory() as session:
        # Try both platforms
        results_tiktok = await query_market_trends(session, category, "tiktok_shop", country, limit=6)
        results_shopee = await query_market_trends(session, category, "shopee", country, limit=6)

    source_url = dataset_url("market_trends", category=category, country=country)

    all_results = results_tiktok + results_shopee
    if not all_results:
        return {"found": False, "message": f"No trend data for {category} in {country}", "source_url": source_url}

    # Aggregate
    volumes = [r.search_volume for r in all_results if r.search_volume]
    growths = [float(r.growth_rate_pct) for r in all_results if r.growth_rate_pct is not None]
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    avg_growth = sum(growths) / len(growths) if growths else 0

    return {
        "found": True,
        "category": category,
        "country": country,
        "avg_search_volume": int(avg_volume),
        "avg_growth_rate_pct": round(avg_growth, 2),
        "trend_direction": "rising" if avg_growth > 10 else ("stable" if avg_growth > -5 else "declining"),
        "data_points": len(all_results),
        "source_url": source_url,
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def get_category_growth(category: str, platform: str, country: str) -> dict:
    """Get growth rate and momentum for a category on a specific platform and country."""
    async with async_session_factory() as session:
        results = await query_market_trends(session, category, platform, country, limit=12)

    source_url = dataset_url("market_trends", category=category, platform=platform, country=country)

    if not results:
        return {
            "found": False,
            "message": f"No growth data for {category} on {platform} in {country}",
            "source_url": source_url,
        }

    growths = [float(r.growth_rate_pct) for r in results if r.growth_rate_pct is not None]
    avg_growth = sum(growths) / len(growths) if growths else 0

    # Trend direction
    if len(growths) >= 3:
        recent = sum(growths[:3]) / 3
        older = sum(growths[3:6]) / min(len(growths[3:6]), 3) if len(growths) > 3 else recent
        momentum = "accelerating" if recent > older else ("decelerating" if recent < older else "steady")
    else:
        momentum = "unknown"

    return {
        "found": True,
        "category": category,
        "platform": platform,
        "country": country,
        "avg_growth_rate_pct": round(avg_growth, 2),
        "momentum": momentum,
        "months_available": len(results),
        "source_url": source_url,
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def get_influencer_data(category: str, country: str) -> dict:
    """Get influencer and creator activity data for a category in a country.

    Returns top influencer mentions and creator seller counts.
    """
    async with async_session_factory() as session:
        results_tiktok = await query_market_trends(session, category, "tiktok_shop", country, limit=6)
        results_shopee = await query_market_trends(session, category, "shopee", country, limit=6)

    source_url = dataset_url("market_trends", category=category, country=country)

    all_results = results_tiktok + results_shopee
    if not all_results:
        return {"found": False, "message": f"No influencer data for {category} in {country}", "source_url": source_url}

    mentions = [r.influencer_mentions for r in all_results]
    sellers = [r.creator_sellers for r in all_results]
    avg_mentions = sum(mentions) / len(mentions) if mentions else 0
    avg_sellers = sum(sellers) / len(sellers) if sellers else 0

    return {
        "found": True,
        "category": category,
        "country": country,
        "avg_influencer_mentions": round(avg_mentions, 1),
        "avg_creator_sellers": round(avg_sellers, 1),
        "max_influencer_mentions": max(mentions) if mentions else 0,
        "max_creator_sellers": max(sellers) if sellers else 0,
        "source_url": source_url,
        "fetch_time": datetime.now().isoformat(),
    }
