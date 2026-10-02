"""Seven-dimension scoring for decision review."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.evidence.models import EvidenceDimension, EvidenceItem


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


def score_dimension(
    dimension: str,
    evidence_items: list[EvidenceItem],
) -> DimensionScore:
    """Score a single dimension from its evidence items.

    Uses a heuristic: weighted average of evidence values, mapped to 0-10.
    For risk dimensions (compliance_risk), higher risk → lower score.
    """
    if not evidence_items:
        return DimensionScore(
            dimension=dimension,
            score=5.0,  # neutral when no evidence
            evidence_count=0,
            confidence=0.0,
        )

    # Average confidence
    avg_confidence = float(sum(i.confidence for i in evidence_items) / len(evidence_items))

    # Extract numeric values
    values = [float(i.value) for i in evidence_items if i.value is not None]
    if not values:
        # No numeric evidence — use confidence as proxy
        return DimensionScore(
            dimension=dimension,
            score=avg_confidence * 10,
            evidence_count=len(evidence_items),
            confidence=avg_confidence,
        )

    # Score computation depends on dimension
    if dimension == "market_demand":
        # Search volume → score (log scale, 10K→3, 100K→5, 1M→8, 10M→10)
        import math
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, 2.0 + 1.5 * math.log10(max(avg_val, 1) / 10000)))

    elif dimension == "competition":
        # More sellers → lower score (inverse)
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, 10.0 - avg_val * 0.5))

    elif dimension == "cost_margin":
        # Margin % → score (15%→5, 30%→7, 50%→9)
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, avg_val / 5.0))

    elif dimension == "compliance_risk":
        # Risk items count → inverse score (0 blocks → 10, 1 block → 3, 2+ → 1)
        block_count = sum(1 for i in evidence_items if i.dimension == EvidenceDimension.COMPLIANCE_BLOCK)
        if block_count >= 2:
            score = 1.0
        elif block_count == 1:
            score = 3.0
        else:
            warn_count = sum(1 for i in evidence_items if i.dimension == EvidenceDimension.COMPLIANCE_WARN)
            score = max(4.0, 10.0 - warn_count * 1.5)

    elif dimension == "supply_stability":
        # More suppliers → higher score
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, avg_val))

    elif dimension == "trend_momentum":
        # Growth rate % → score (-15→1, 0→4, 20→7, 40→10)
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, 4.0 + avg_val / 8.0))

    elif dimension == "return_rate":
        # Return rate % → inverse score (5%→9, 10%→7, 20%→3)
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, 10.0 - avg_val * 0.5))

    else:
        # Generic: map average value to 0-10
        avg_val = sum(values) / len(values)
        score = min(10.0, max(0.0, avg_val))

    return DimensionScore(
        dimension=dimension,
        score=round(score, 1),
        evidence_count=len(evidence_items),
        confidence=round(avg_confidence, 2),
    )


def score_all_dimensions(
    evidence_by_dimension: dict[str, list[EvidenceItem]],
) -> ScoreResult:
    """Score all 7 dimensions and compute overall score."""
    dimension_scores: list[DimensionScore] = []
    scores_dict: dict[str, float] = {}

    for dim in ALL_DIMENSIONS:
        items = evidence_by_dimension.get(dim, [])
        ds = score_dimension(dim, items)
        dimension_scores.append(ds)
        scores_dict[dim] = ds.score

    # Weighted composite
    overall = sum(scores_dict[d] * DIMENSION_WEIGHTS[d] for d in ALL_DIMENSIONS)
    overall = round(overall, 2)

    return ScoreResult(
        dimensions=dimension_scores,
        overall_score=overall,
        scores_dict=scores_dict,
    )
