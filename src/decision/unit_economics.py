"""Platform-specific unit economics models — P&L breakdown for TikTok Shop and Shopee."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.config.platform_profiles import get_profile


@dataclass
class UnitEconomics:
    """Full P&L breakdown for a single unit."""

    retail_price: Decimal
    product_cost: Decimal
    freight_cost: Decimal
    platform_commission: Decimal
    platform_commission_pct: Decimal
    payment_processing: Decimal
    payment_processing_pct: Decimal
    creator_commission: Decimal
    creator_commission_pct: Decimal
    packaging: Decimal
    import_duty: Decimal
    import_duty_pct: Decimal
    return_allowance: Decimal
    return_rate_pct: Decimal
    other_costs: Decimal

    @property
    def total_cost(self) -> Decimal:
        return (
            self.product_cost
            + self.freight_cost
            + self.platform_commission
            + self.payment_processing
            + self.creator_commission
            + self.packaging
            + self.import_duty
            + self.return_allowance
            + self.other_costs
        )

    @property
    def gross_profit(self) -> Decimal:
        return self.retail_price - self.product_cost - self.freight_cost

    @property
    def gross_margin_pct(self) -> Decimal:
        if self.retail_price == 0:
            return Decimal("0")
        return (self.gross_profit / self.retail_price * 100).quantize(Decimal("0.01"))

    @property
    def net_profit(self) -> Decimal:
        return self.retail_price - self.total_cost

    @property
    def net_margin_pct(self) -> Decimal:
        if self.retail_price == 0:
            return Decimal("0")
        return (self.net_profit / self.retail_price * 100).quantize(Decimal("0.01"))

    @property
    def breakeven_units_per_month(self) -> Decimal:
        """Rough breakeven: fixed costs not included, just margin per unit."""
        if self.net_profit <= 0:
            return Decimal("Infinity")
        return Decimal("1")  # Per unit is always profitable if net_profit > 0

    def to_dict(self) -> dict:
        return {
            "retail_price": float(self.retail_price),
            "product_cost": float(self.product_cost),
            "freight_cost": float(self.freight_cost),
            "platform_commission": float(self.platform_commission),
            "platform_commission_pct": float(self.platform_commission_pct),
            "payment_processing": float(self.payment_processing),
            "payment_processing_pct": float(self.payment_processing_pct),
            "creator_commission": float(self.creator_commission),
            "creator_commission_pct": float(self.creator_commission_pct),
            "packaging": float(self.packaging),
            "import_duty": float(self.import_duty),
            "import_duty_pct": float(self.import_duty_pct),
            "return_allowance": float(self.return_allowance),
            "return_rate_pct": float(self.return_rate_pct),
            "other_costs": float(self.other_costs),
            "gross_profit": float(self.gross_profit),
            "gross_margin_pct": float(self.gross_margin_pct),
            "net_profit": float(self.net_profit),
            "net_margin_pct": float(self.net_margin_pct),
            "total_cost": float(self.total_cost),
        }


def calculate_unit_economics(
    platform: str,
    category: str,
    retail_price_usd: float,
    product_cost_usd: float,
    freight_cost_usd: float,
    creator_commission_pct: float | None = None,
    import_duty_pct: float = 0.0,
    return_rate_pct: float | None = None,
    packaging_usd: float = 0.5,
) -> UnitEconomics:
    """Calculate full unit economics for a product on a platform.

    Uses the platform profile to fill in default commission rates, payment processing,
    and return rates when not explicitly provided.
    """
    profile = get_profile(platform)
    retail = Decimal(str(retail_price_usd)).quantize(Decimal("0.01"))

    # Platform commission
    from src.config.platform_profiles import get_commission_rate
    comm_pct = Decimal(str(get_commission_rate(platform, category) / 100))
    comm = (retail * comm_pct).quantize(Decimal("0.01"))

    # Payment processing
    pp_pct = Decimal(str(profile.payment_processing_pct / 100))
    pp = (retail * pp_pct).quantize(Decimal("0.01"))

    # Creator/affiliate commission
    if creator_commission_pct is None:
        avg_creator = (profile.creator_commission_min_pct + profile.creator_commission_max_pct) / 2
        creator_commission_pct = avg_creator
    creator_pct = Decimal(str(creator_commission_pct / 100))
    creator_comm = (retail * creator_pct).quantize(Decimal("0.01"))

    # Return rate
    if return_rate_pct is None:
        return_rate_pct = profile.typical_return_rate_pct
    rr_pct = Decimal(str(return_rate_pct / 100))
    return_allowance = (retail * rr_pct).quantize(Decimal("0.01"))

    # Import duty
    duty_pct = Decimal(str(import_duty_pct / 100))
    duty = (retail * duty_pct).quantize(Decimal("0.01"))

    return UnitEconomics(
        retail_price=retail,
        product_cost=Decimal(str(product_cost_usd)).quantize(Decimal("0.01")),
        freight_cost=Decimal(str(freight_cost_usd)).quantize(Decimal("0.01")),
        platform_commission=comm,
        platform_commission_pct=(comm_pct * 100).quantize(Decimal("0.01")),
        payment_processing=pp,
        payment_processing_pct=(pp_pct * 100).quantize(Decimal("0.01")),
        creator_commission=creator_comm,
        creator_commission_pct=(creator_pct * 100).quantize(Decimal("0.01")),
        packaging=Decimal(str(packaging_usd)).quantize(Decimal("0.01")),
        import_duty=duty,
        import_duty_pct=(duty_pct * 100).quantize(Decimal("0.01")),
        return_allowance=return_allowance,
        return_rate_pct=(rr_pct * 100).quantize(Decimal("0.01")),
        other_costs=Decimal("0"),
    )
