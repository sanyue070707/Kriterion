"""Test configuration and fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_candidate_raw():
    """Sample raw candidate data for testing."""
    return {
        "id": "test-001",
        "name": "Vitamin C Serum #123",
        "category": "beauty",
        "subcategory": "skincare",
        "platform": "tiktok_shop",
        "source_country": "CN",
        "target_country": "US",
        "price_usd": 25.99,
        "currency": "USD",
        "moq": 100,
        "weight_kg": 0.15,
        "metadata": {"supplier_id": "SUP-1234", "has_brand": True},
    }


@pytest.fixture
def sample_candidate_raw_shopee():
    """Sample Shopee candidate for testing."""
    return {
        "id": "test-002",
        "name": "Wireless Earbuds TWS #456",
        "category": "electronics",
        "platform": "shopee",
        "source_country": "CN",
        "target_country": "ID",
        "price_usd": 15.50,
        "currency": "USD",
        "moq": 200,
        "weight_kg": 0.05,
        "metadata": {"supplier_id": "SUP-5678"},
    }
