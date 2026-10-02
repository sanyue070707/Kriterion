"""Seven-dimension scoring for decision review.

Evidence is authored in fine-grained dimensions (see `EvidenceDimension`);
`DIMENSION_EVIDENCE` maps those into the seven scoring dimensions, so each
dimension is scored from the evidence that actually backs it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.evidence.models import EvidenceDimension as ED
from src.evidence.models import EvidenceItem

# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS: dict[str, float] = {
    "market_demand": 0.20,
    "competition": 0.10,
    "cost_margin": 0.25,
    "compliance_risk": 0.20,
    "supply_stability": 0.10,
    "trend_momentum": 0.10,
    "return_rate": 0.05,
}

ALL_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())

# Evidence dimension -> scoring dimension. Dimensions not listed here
# (e.g. certification counts, policy references) inform the ledger but
# deliberately do not move the score.
DIMENSION_EVIDENCE: dict[str, list[ED]] = {
    "market_demand": [ED.MARKET_DEMAND],
    "competition": [ED.COMPETITION],
    "cost_margin": [ED.NET_MARGIN, ED.GROSS_MARGIN],
    "compliance_risk": [ED.COMPLIANCE_BLOCK, ED.COMPLIANCE_WARN, ED.TRADEMARK_RISK],
    "supply_stability": [ED.SUPPLY_STABILITY],
    "trend_momentum": [ED.TREND_MOMENTUM],
    "return_rate": [ED.RETURN_RATE],
}

_DIMENSION_OF: dict[ED, str] = {
    evidence_dim: score_dim
    for score_dim, evidence_dims in DIMENSION_EVIDENCE.items()
    for evidence_dim in evidence_dims
}


def bucket_evidence(items: list[EvidenceItem]) -> dict[str, list[EvidenceItem]]:
    """Group evidence items into the seven scoring dimensions."""
    buckets: dict[str, list[EvidenceItem]] = {dim: [] for dim in ALL_DIMENSIONS}
    for item in items:
        scoring_dim = _DIMENSION_OF.get(item.dimension)
        if scoring_dim is not None:
            buckets[scoring_dim].append(item)
    return buckets


@dataclass
class DimensionScore:
    dimension: str
    score: float  # 0-10
    evidence_count: int
    confidence: float  # average confidence of contributing evidence


@dataclass
class ScoreResult:
    dimensions: list[DimensionScore]
    overall_score: float  # weighted composite 0-10
    scores_dict: dict[str, float]


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return min(high, max(low, value))


def _values(evidence_items: list[EvidenceItem], dimension: ED | None = None) -> list[float]:
    return [
        float(i.value)
        for i in evidence_items
        if i.value is not None and (dimension is None or i.dimension == dimension)
    ]


def score_dimension(dimension: str, evidence_items: list[EvidenceItem]) -> DimensionScore:
    """Score a single dimension from its evidence items (0-10).

    Risk dimensions invert: more blocks / conflicts => lower score.
    """
    if not evidence_items:
        return DimensionScore(dimension, 5.0, 0, 0.0)  # neutral when no evidence

    avg_confidence = float(sum(i.confidence for i in evidence_items) / len(evidence_items))
    values = _values(evidence_items)

    if not values:
        # No numeric evidence — fall back to the confidence as a weak proxy.
        return DimensionScore(dimension, round(avg_confidence * 10, 1), len(evidence_items), round(avg_confidence, 2))

    if dimension == "market_demand":
        # Search volume → score (log scale: 10K→3, 1M→8)
        avg_val = sum(values) / len(values)
        score = 2.0 + 1.5 * math.log10(max(avg_val, 1) / 10000)

    elif dimension == "competition":
        # More creator-sellers → lower score
        avg_val = sum(values) / len(values)
        score = 10.0 - avg_val * 0.5

    elif dimension == "cost_margin":
        # Prefer net margin when present; fall back to gross margin.
        vals = _values(evidence_items, ED.NET_MARGIN) or _values(evidence_items, ED.GROSS_MARGIN) or values
        avg_val = sum(vals) / len(vals)
        score = avg_val / 5.0  # 15%→3, 30%→6, 45%→9

    elif dimension == "compliance_risk":
        blocks = max(_values(evidence_items, ED.COMPLIANCE_BLOCK), default=0.0)
        trademark = max(_values(evidence_items, ED.TRADEMARK_RISK), default=0.0)
        warn_count = len([v for v in _values(evidence_items, ED.COMPLIANCE_WARN) if v > 0])
        if blocks >= 2:
            score = 1.0
        elif blocks == 1:
            score = 3.0
        else:
            score = 10.0 - min(warn_count, 4) * 1.0 - (3.0 if trademark > 0 else 0.0)
            score = max(2.0, score)

    elif dimension == "supply_stability":
        # Distinct supplier count → score (1→3.7, 5→6.5, 10→10)
        avg_val = sum(values) / len(values)
        score = 3.0 + avg_val * 0.7

    elif dimension == "trend_momentum":
        # Growth rate % → score (-15→2, 0→4, 40→9)
        avg_val = sum(values) / len(values)
        score = 4.0 + avg_val / 8.0

    elif dimension == "return_rate":
        # Return rate % → inverse score (5%→7.5, 20%→0)
        avg_val = sum(values) / len(values)
        score = 10.0 - avg_val * 0.5

    else:
        avg_val = sum(values) / len(values)
        score = avg_val

    return DimensionScore(
        dimension=dimension,
        score=round(_clamp(score), 1),
        evidence_count=len(evidence_items),
        confidence=round(avg_confidence, 2),
    )


def score_all_dimensions(
    evidence_by_dimension: dict[str, list[EvidenceItem]],
) -> ScoreResult:
    """Score all 7 dimensions and compute the weighted composite."""
    dimension_scores: list[DimensionScore] = []
    scores_dict: dict[str, float] = {}

    for dim in ALL_DIMENSIONS:
        items = evidence_by_dimension.get(dim, [])
        ds = score_dimension(dim, items)
        dimension_scores.append(ds)
        scores_dict[dim] = ds.score

    overall = sum(scores_dict[d] * DIMENSION_WEIGHTS[d] for d in ALL_DIMENSIONS)
    overall = round(overall, 2)

    return ScoreResult(
        dimensions=dimension_scores,
        overall_score=overall,
        scores_dict=scores_dict,
    )
