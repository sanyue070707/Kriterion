"""Evidence merge — combine evidence from 3 parallel agents, deduplicate."""

from __future__ import annotations

from src.evidence.models import AgentType, EvidenceItem


def _dedup_key(item: EvidenceItem) -> str:
    """Dedup key: same agent + dimension + claim (normalized)."""
    return f"{item.agent_type.value}:{item.dimension.value}:{item.claim.strip().lower()}"


def merge_evidence(
    trend_items: list[EvidenceItem],
    supply_items: list[EvidenceItem],
    compliance_items: list[EvidenceItem],
) -> list[EvidenceItem]:
    """Merge evidence from all 3 agents, deduplicating by agent+dimension+claim.

    When duplicates are found, keep the one with higher confidence.
    """
    all_items = trend_items + supply_items + compliance_items

    # Deduplicate
    seen: dict[str, EvidenceItem] = {}
    for item in all_items:
        key = _dedup_key(item)
        if key not in seen or item.confidence > seen[key].confidence:
            seen[key] = item

    return list(seen.values())


def group_by_agent(items: list[EvidenceItem]) -> dict[AgentType, list[EvidenceItem]]:
    """Group evidence items by agent type."""
    groups: dict[AgentType, list[EvidenceItem]] = {at: [] for at in AgentType}
    for item in items:
        groups[item.agent_type].append(item)
    return groups
