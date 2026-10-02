"""Platform-specific unit economics models for TikTok Shop and Shopee.

Each profile defines:
- commission rate ranges by category
- payment processing fee
- typical creator/influencer commission range
- mandatory cost items
- sensitivity axes (what drives profit variance)
- quick-screen thresholds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Platform(str, Enum):
    TIKTOK_SHOP = "tiktok_shop"
    SHOPEE = "shopee"


@dataclass
class CommissionTier:
    category: str
    rate_min_pct: float
    rate_max_pct: float
    typical_pct: float


@dataclass
class PlatformProfile:
    platform: Platform
    display_name: str
    payment_processing_pct: float
    commission_tiers: list[CommissionTier]
    creator_commission_min_pct: float
    creator_commission_max_pct: float
    mandatory_cost_items: list[str]
    sensitivity_axes: list[str]
    min_viable_margin_pct: float
    max_return_rate_pct: float
    typical_return_rate_pct: float


# ── TikTok Shop Profile ──
TIKTOK_SHOP_PROFILE = PlatformProfile(
    platform=Platform.TIKTOK_SHOP,
    display_name="TikTok Shop",
    payment_processing_pct=1.5,
    commission_tiers=[
        CommissionTier("beauty", 2.0, 5.0, 3.5),
        CommissionTier("electronics", 3.0, 6.0, 4.5),
        CommissionTier("home_living", 2.0, 4.0, 3.0),
        CommissionTier("fashion", 3.0, 5.0, 4.0),
        CommissionTier("food_beverage", 1.0, 3.0, 2.0),
        CommissionTier("pet_supplies", 2.5, 5.0, 3.5),
        CommissionTier("toys", 2.0, 4.0, 3.0),
    ],
    creator_commission_min_pct=10.0,
    creator_commission_max_pct=25.0,
    mandatory_cost_items=[
        "product_cost",
        "freight",
        "platform_commission",
        "payment_processing",
        "creator_commission",
        "packaging",
        "return_allowance",
    ],
    sensitivity_axes=["creator_commission", "freight_mode", "return_rate"],
    min_viable_margin_pct=15.0,
    max_return_rate_pct=25.0,
    typical_return_rate_pct=8.0,
)

# ── Shopee Profile ──
SHOPEE_PROFILE = PlatformProfile(
    platform=Platform.SHOPEE,
    display_name="Shopee",
    payment_processing_pct=2.0,
    commission_tiers=[
        CommissionTier("beauty", 3.0, 8.0, 5.0),
        CommissionTier("electronics", 4.0, 8.0, 6.0),
        CommissionTier("home_living", 3.0, 6.0, 4.5),
        CommissionTier("fashion", 4.0, 7.0, 5.5),
        CommissionTier("food_beverage", 2.0, 5.0, 3.0),
        CommissionTier("pet_supplies", 3.5, 7.0, 5.0),
        CommissionTier("toys", 3.0, 6.0, 4.5),
    ],
    creator_commission_min_pct=5.0,
    creator_commission_max_pct=15.0,
    mandatory_cost_items=[
        "product_cost",
        "freight",
        "platform_commission",
        "payment_processing",
        "affiliate_commission",
        "packaging",
        "return_allowance",
        "vat_gst",
    ],
    sensitivity_axes=["affiliate_commission", "import_duty", "return_rate"],
    min_viable_margin_pct=12.0,
    max_return_rate_pct=20.0,
    typical_return_rate_pct=6.0,
)

PROFILES: dict[Platform, PlatformProfile] = {
    Platform.TIKTOK_SHOP: TIKTOK_SHOP_PROFILE,
    Platform.SHOPEE: SHOPEE_PROFILE,
}


def get_profile(platform: str) -> PlatformProfile:
    """Get platform profile by name string."""
    key = Platform(platform)
    return PROFILES[key]


def get_commission_rate(platform: str, category: str) -> float:
    """Get typical commission rate for a platform + category."""
    profile = get_profile(platform)
    for tier in profile.commission_tiers:
        if tier.category == category:
            return tier.typical_pct
    # Default: average of all tiers
    return sum(t.typical_pct for t in profile.commission_tiers) / len(profile.commission_tiers)
