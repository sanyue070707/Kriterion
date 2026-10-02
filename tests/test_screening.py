"""Tests for screening — normalization and funnel."""

from decimal import Decimal

from src.screening.normalize import (
    NormalizedCandidate,
    convert_to_usd,
    normalize_candidate,
    normalize_category,
    normalize_country,
    normalize_platform,
)
from src.screening.funnel import screen_candidate


class TestNormalize:
    def test_normalize_category_exact(self):
        assert normalize_category("beauty") == "beauty"

    def test_normalize_category_alias(self):
        assert normalize_category("skincare") == "beauty"
        assert normalize_category("cosmetics") == "beauty"

    def test_normalize_category_case_insensitive(self):
        assert normalize_category("ELECTRONICS") == "electronics"

    def test_normalize_country_code(self):
        assert normalize_country("cn") == "CN"
        assert normalize_country("US") == "US"

    def test_normalize_country_name(self):
        assert normalize_country("china") == "CN"
        assert normalize_country("japan") == "JP"

    def test_normalize_platform_tiktok(self):
        assert normalize_platform("TikTok Shop") == "tiktok_shop"
        assert normalize_platform("tiktok-shop") == "tiktok_shop"

    def test_normalize_platform_shopee(self):
        assert normalize_platform("Shopee") == "shopee"

    def test_convert_to_usd_identity(self):
        assert convert_to_usd(Decimal("100"), "USD") == Decimal("100.00")

    def test_convert_to_usd_cny(self):
        result = convert_to_usd(Decimal("100"), "CNY")
        assert result > 0
        assert result < Decimal("20")  # 100 CNY ≈ 14 USD

    def test_normalize_candidate_full(self, sample_candidate_raw):
        result = normalize_candidate(sample_candidate_raw)
        assert isinstance(result, NormalizedCandidate)
        assert result.category == "beauty"
        assert result.platform == "tiktok_shop"
        assert result.source_country == "CN"
        assert result.target_country == "US"
        assert result.price_usd > 0


class TestFunnel:
    def _make_normalized(self, **overrides) -> NormalizedCandidate:
        defaults = {
            "id": "test",
            "name": "Test Product",
            "category": "beauty",
            "subcategory": "",
            "platform": "tiktok_shop",
            "source_country": "CN",
            "target_country": "US",
            "price_usd": Decimal("25.99"),
            "moq": 100,
            "weight_kg": Decimal("0.15"),
            "metadata": {},
        }
        defaults.update(overrides)
        return NormalizedCandidate(**defaults)

    def test_screen_passes_valid_candidate(self):
        candidate = self._make_normalized()
        result = screen_candidate(candidate)
        assert result.passed

    def test_screen_rejects_invalid_category(self):
        candidate = self._make_normalized(category="weapons")
        result = screen_candidate(candidate)
        assert not result.passed
        assert any("Category" in r for r in result.reject_reasons)

    def test_screen_rejects_invalid_platform(self):
        candidate = self._make_normalized(platform="amazon")
        result = screen_candidate(candidate)
        assert not result.passed

    def test_screen_rejects_too_expensive(self):
        candidate = self._make_normalized(price_usd=Decimal("600"))
        result = screen_candidate(candidate)
        assert not result.passed
        assert any("Price" in r for r in result.reject_reasons)

    def test_screen_rejects_too_heavy(self):
        candidate = self._make_normalized(weight_kg=Decimal("35"))
        result = screen_candidate(candidate)
        assert not result.passed
