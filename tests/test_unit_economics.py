"""Tests for unit economics model."""

from decimal import Decimal

from src.decision.unit_economics import UnitEconomics, calculate_unit_economics


class TestUnitEconomics:
    def test_calculate_tiktok_shop(self):
        ue = calculate_unit_economics(
            platform="tiktok_shop",
            category="beauty",
            retail_price_usd=25.99,
            product_cost_usd=8.50,
            freight_cost_usd=0.30,
            creator_commission_pct=15.0,
            import_duty_pct=0.0,
        )
        assert ue.retail_price == Decimal("25.99")
        assert ue.product_cost == Decimal("8.50")
        assert ue.freight_cost == Decimal("0.30")
        assert ue.gross_profit > 0
        assert ue.gross_margin_pct > 0
        assert ue.net_margin_pct > 0
        assert ue.total_cost > 0

    def test_calculate_shopee(self):
        ue = calculate_unit_economics(
            platform="shopee",
            category="electronics",
            retail_price_usd=59.99,
            product_cost_usd=20.00,
            freight_cost_usd=1.50,
            creator_commission_pct=10.0,
            import_duty_pct=5.0,
        )
        assert ue.retail_price == Decimal("59.99")
        assert ue.net_profit > 0

    def test_profitability(self):
        ue = calculate_unit_economics(
            platform="tiktok_shop",
            category="fashion",
            retail_price_usd=30.00,
            product_cost_usd=5.00,
            freight_cost_usd=0.50,
        )
        assert ue.net_profit > 0
        assert ue.net_margin_pct > Decimal("0")

    def test_unprofitable(self):
        ue = calculate_unit_economics(
            platform="shopee",
            category="electronics",
            retail_price_usd=10.00,
            product_cost_usd=9.00,
            freight_cost_usd=2.00,
            creator_commission_pct=15.0,
        )
        assert ue.net_profit < 0

    def test_to_dict(self):
        ue = calculate_unit_economics(
            platform="tiktok_shop",
            category="beauty",
            retail_price_usd=25.99,
            product_cost_usd=8.50,
            freight_cost_usd=0.30,
        )
        d = ue.to_dict()
        assert "retail_price" in d
        assert "net_profit" in d
        assert "net_margin_pct" in d
        assert isinstance(d["retail_price"], float)
