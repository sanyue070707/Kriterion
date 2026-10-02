"""Evidence Gatekeeper — validate, strip unsourced numbers, check confidence.

The gatekeeper enforces the core constraint: no business number may exist in the
decision card without a verifiable source. It:
1. Strips evidence items without a source_tool
2. Flags items with confidence < threshold
3. Flags items with expired data
4. Produces a GatekeeperReport
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from src.evidence.models import EvidenceItem, GatekeeperReport

# Default thresholds
MIN_CONFIDENCE = Decimal("0.50")
MIN_FRESHNESS_HOURS = 48  # data must be less than this old


def gatekeep(
    evidence_items: Sequence[EvidenceItem],
    min_confidence: Decimal = MIN_CONFIDENCE,
) -> tuple[list[EvidenceItem], GatekeeperReport]:
    """Apply gatekeeping rules to a list of evidence items.

    Returns:
        - List of validated (gated) evidence items
        - GatekeeperReport summarizing what was stripped/flagged
    """
    valid_items: list[EvidenceItem] = []
    stripped_count = 0
    low_confidence_count = 0
    expired_count = 0
    stripped_reasons: list[str] = []

    for item in evidence_items:
        # Rule 1: Must have a source tool
        if not item.has_source:
            stripped_count += 1
            reason = f"Stripped: '{item.claim[:50]}' — no source tool"
            stripped_reasons.append(reason)
            continue

        # Rule 2: Confidence check
        if item.confidence < min_confidence:
            low_confidence_count += 1
            # Don't strip, but flag
            stripped_reasons.append(
                f"Flagged: '{item.claim[:50]}' — low confidence {item.confidence}"
            )

        # Rule 3: Expiration check
        if item.is_expired:
            expired_count += 1
            stripped_reasons.append(
                f"Flagged: '{item.claim[:50]}' — data expired"
            )
            continue  # Strip expired items

        valid_items.append(item)

    # Compute confidence summary by agent_type
    confidence_by_agent: dict[str, list[Decimal]] = {}
    for item in valid_items:
        key = item.agent_type.value
        confidence_by_agent.setdefault(key, []).append(item.confidence)

    confidence_summary = {
        key: float(sum(vals) / len(vals))
        for key, vals in confidence_by_agent.items()
    }

    report = GatekeeperReport(
        total_items=len(evidence_items),
        valid_items=len(valid_items),
        stripped_items=stripped_count,
        low_confidence_items=low_confidence_count,
        expired_items=expired_count,
        stripped_reasons=stripped_reasons,
        confidence_summary=confidence_summary,
    )

    return valid_items, report
