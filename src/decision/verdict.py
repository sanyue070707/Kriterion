"""Verdict logic — Go / Watch / No-Go decision."""

from __future__ import annotations

from dataclasses import dataclass

from src.evidence.models import EvidenceDimension, EvidenceItem


@dataclass
class VerdictResult:
    verdict: str  # "go" | "watch" | "no_go"
    reason: str


def compute_verdict(
    overall_score: float,
    scores: dict[str, float],
    evidence_items: list[EvidenceItem],
    min_margin_pct: float = 15.0,
) -> VerdictResult:
    """Compute Go / Watch / No-Go verdict.

    Rules:
    - No-Go: overall < 4.0, OR any compliance block, OR margin below minimum
    - Go: overall >= 7.0, AND no compliance blocks, AND margin above threshold
    - Watch: everything else
    """
    # Check for compliance blocks
    has_compliance_block = any(
        i.dimension == EvidenceDimension.COMPLIANCE_BLOCK and i.value is not None and float(i.value) > 0
        for i in evidence_items
    )

    # Check margin
    margin_score = scores.get("cost_margin", 5.0)
    margin_adequate = margin_score >= (min_margin_pct / 5.0)  # score_dimension maps margin%/5

    # No-Go conditions
    if has_compliance_block:
        return VerdictResult("no_go", "Compliance block(s) identified — product cannot be listed")

    if overall_score < 4.0:
        return VerdictResult("no_go", f"Overall score {overall_score} below threshold 4.0")

    if not margin_adequate:
        return VerdictResult("no_go", f"Margin insufficient (score {margin_score}, need {min_margin_pct / 5.0:.1f})")

    # Go conditions
    if overall_score >= 7.0 and margin_adequate and not has_compliance_block:
        return VerdictResult("go", f"Strong candidate: score {overall_score}, margin adequate, no compliance blocks")

    # Watch
    watch_reasons = []
    if overall_score < 7.0:
        watch_reasons.append(f"Score {overall_score} below Go threshold 7.0")
    if scores.get("compliance_risk", 10) < 7:
        watch_reasons.append("Compliance warnings present")
    if scores.get("supply_stability", 10) < 5:
        watch_reasons.append("Supply stability concern")

    return VerdictResult(
        "watch",
        f"Conditional: {'; '.join(watch_reasons) if watch_reasons else 'moderate scores across dimensions'}",
    )
