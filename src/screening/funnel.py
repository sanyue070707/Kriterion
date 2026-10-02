"""Quick screening funnel — reject candidates that clearly can't pass evaluation.

Screening criteria (configurable per platform):
1. Price range: too cheap or too expensive
2. Category whitelist: only known categories
3. Weight: too heavy for e-commerce shipping
4. Platform validity: must be tiktok_shop or shopee
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config.platform_profiles import Platform, get_profile
from src.screening.normalize import NormalizedCandidate

# Category whitelist
VALID_CATEGORIES = {"beauty", "electronics", "home_living", "fashion", "food_beverage", "pet_supplies", "toys"}

# Global screening thresholds
MAX_PRICE_USD = 500.0
MIN_PRICE_USD = 1.0
MAX_WEIGHT_KG = 30.0  # beyond this, shipping is prohibitive for most e-commerce


@dataclass
class ScreeningResult:
    passed: bool
    reject_reasons: list[str]

    @property
    def reject_reason(self) -> str | None:
        return "; ".join(self.reject_reasons) if self.reject_reasons else None


def screen_candidate(candidate: NormalizedCandidate) -> ScreeningResult:
    """Apply quick screening funnel to a normalized candidate.

    Returns ScreeningResult with pass/fail and reasons.
    """
    reasons: list[str] = []

    # 1. Category check
    if candidate.category not in VALID_CATEGORIES:
        reasons.append(f"Category '{candidate.category}' not in whitelist")

    # 2. Platform check
    valid_platforms = {p.value for p in Platform}
    if candidate.platform not in valid_platforms:
        reasons.append(f"Platform '{candidate.platform}' not supported")

    # 3. Price range check
    if candidate.price_usd < MIN_PRICE_USD:
        reasons.append(f"Price ${candidate.price_usd} below minimum ${MIN_PRICE_USD}")
    if candidate.price_usd > MAX_PRICE_USD:
        reasons.append(f"Price ${candidate.price_usd} above maximum ${MAX_PRICE_USD}")

    # 4. Weight check
    if candidate.weight_kg > MAX_WEIGHT_KG:
        reasons.append(f"Weight {candidate.weight_kg}kg exceeds max {MAX_WEIGHT_KG}kg")

    # 5. Platform-specific margin threshold hint
    try:
        profile = get_profile(candidate.platform)
        # Check if the candidate's category exists in profile
        cats = [t.category for t in profile.commission_tiers]
        if candidate.category not in cats:
            reasons.append(f"Category '{candidate.category}' not configured for {profile.display_name}")
    except (KeyError, ValueError):
        pass  # already caught by platform check

    return ScreeningResult(
        passed=len(reasons) == 0,
        reject_reasons=reasons,
    )
