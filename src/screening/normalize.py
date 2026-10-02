"""Candidate normalization — standardize fields before screening."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


# Category alias mapping (variant → canonical)
CATEGORY_ALIASES: dict[str, str] = {
    "beauty": "beauty",
    "cosmetics": "beauty",
    "skincare": "beauty",
    "makeup": "beauty",
    "electronics": "electronics",
    "tech": "electronics",
    "gadgets": "electronics",
    "home_living": "home_living",
    "home": "home_living",
    "household": "home_living",
    "kitchen": "home_living",
    "fashion": "fashion",
    "apparel": "fashion",
    "clothing": "fashion",
    "food_beverage": "food_beverage",
    "food": "food_beverage",
    "snacks": "food_beverage",
    "pet_supplies": "pet_supplies",
    "pets": "pet_supplies",
    "toys": "toys",
    "games": "toys",
}

# Currency → USD exchange rates (approximate)
USD_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "CNY": Decimal("0.14"),
    "GBP": Decimal("1.27"),
    "EUR": Decimal("1.09"),
    "IDR": Decimal("0.000063"),
    "PHP": Decimal("0.018"),
    "MYR": Decimal("0.22"),
    "THB": Decimal("0.029"),
    "KRW": Decimal("0.00075"),
    "JPY": Decimal("0.0067"),
}

# Canonical country codes
COUNTRY_CODES: dict[str, str] = {
    "cn": "CN", "china": "CN", "中国": "CN",
    "kr": "KR", "korea": "KR", "south korea": "KR",
    "jp": "JP", "japan": "JP", "日本": "JP",
    "th": "TH", "thailand": "TH",
    "us": "US", "usa": "US", "united states": "US",
    "uk": "UK", "united kingdom": "UK",
    "id": "ID", "indonesia": "ID",
    "ph": "PH", "philippines": "PH",
    "my": "MY", "malaysia": "MY",
}


@dataclass
class NormalizedCandidate:
    id: str
    name: str
    category: str
    subcategory: str
    platform: str
    source_country: str
    target_country: str
    price_usd: Decimal
    moq: int
    weight_kg: Decimal
    metadata: dict


def normalize_category(raw: str) -> str:
    """Map category variant to canonical name."""
    key = raw.lower().strip().replace(" ", "_").replace("-", "_")
    return CATEGORY_ALIASES.get(key, key)


def normalize_country(raw: str) -> str:
    """Map country variant to ISO 2-letter code."""
    key = raw.lower().strip()
    return COUNTRY_CODES.get(key, raw.upper()[:2])


def normalize_platform(raw: str) -> str:
    """Normalize platform name."""
    p = raw.lower().strip().replace(" ", "_").replace("-", "_")
    if "tiktok" in p:
        return "tiktok_shop"
    if "shopee" in p:
        return "shopee"
    return p


def convert_to_usd(amount: Decimal, currency: str) -> Decimal:
    """Convert an amount to USD."""
    rate = USD_RATES.get(currency.upper(), Decimal("1.0"))
    return (amount * rate).quantize(Decimal("0.01"))


def normalize_candidate(raw: dict) -> NormalizedCandidate:
    """Normalize a raw candidate dict into a standard form."""
    price = Decimal(str(raw.get("price_usd", 0) or 0))
    currency = raw.get("currency", "USD") or "USD"
    if currency != "USD":
        price = convert_to_usd(price, currency)

    return NormalizedCandidate(
        id=str(raw.get("id", "")),
        name=raw.get("name", "").strip(),
        category=normalize_category(raw.get("category", "")),
        subcategory=raw.get("subcategory", "") or "",
        platform=normalize_platform(raw.get("platform", "")),
        source_country=normalize_country(raw.get("source_country", "")),
        target_country=normalize_country(raw.get("target_country", "")),
        price_usd=price,
        moq=int(raw.get("moq", 0) or 0),
        weight_kg=Decimal(str(raw.get("weight_kg", 0) or 0)),
        metadata=raw.get("metadata", {}) or {},
    )
