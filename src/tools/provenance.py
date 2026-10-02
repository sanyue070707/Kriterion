"""Provenance helpers.

Every business number the agents emit must be traceable to the tool call that
produced it. These helpers build the `source_url` reference recorded on each
evidence item, plus a confidence that reflects how much data backed it — so the
evidence ledger is meaningful rather than uniformly "0.80 / unknown".
"""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlencode


def _ref(scheme: str, name: str, params: dict) -> str:
    clean = {k: v for k, v in params.items() if v is not None}
    query = urlencode(sorted(clean.items()))
    return f"{scheme}://{name}" + (f"?{query}" if query else "")


def dataset_url(dataset: str, **filters) -> str:
    """Reference a row set in the local database, e.g.
    `mockdb://market_trends?category=beauty&country=US`."""
    return _ref("mockdb", dataset, filters)


def calc_url(kind: str, **inputs) -> str:
    """Reference a deterministic calculation, e.g.
    `calc://freight?mode=sea&weight_kg=0.15`."""
    return _ref("calc", kind, inputs)


def profile_url(kind: str, **filters) -> str:
    """Reference a static configuration table, e.g. the platform profiles."""
    return _ref("config", kind, filters)


def confidence_from_n(n: int, full_at: int = 8, floor: float = 0.5, ceiling: float = 0.9) -> Decimal:
    """Confidence scaled by sample size: few data points -> lower confidence."""
    if n <= 0:
        return Decimal(str(floor))
    ratio = min(1.0, n / full_at)
    return Decimal(str(round(floor + (ceiling - floor) * ratio, 2)))
