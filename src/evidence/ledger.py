"""Evidence Ledger — append, validate, and manage evidence items.

The ledger is the central store for all evidence collected by the three agents.
Every business number must be bound to a source tool, URL, fetch time, validity, and confidence.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem


class EvidenceLedger:
    """In-memory evidence ledger for a single workflow run."""

    def __init__(self, run_id: str, candidate_id: str) -> None:
        self.run_id = run_id
        self.candidate_id = candidate_id
        self._items: list[EvidenceItem] = []

    def append(self, item: EvidenceItem) -> None:
        """Add an evidence item to the ledger."""
        # Validate that the item belongs to this run
        if item.run_id != self.run_id:
            raise ValueError(f"Evidence item run_id {item.run_id} doesn't match ledger run_id {self.run_id}")
        self._items.append(item)

    def append_many(self, items: list[EvidenceItem]) -> None:
        """Add multiple evidence items."""
        for item in items:
            self.append(item)

    @property
    def items(self) -> list[EvidenceItem]:
        """All evidence items in the ledger."""
        return list(self._items)

    def items_by_agent(self, agent_type: AgentType) -> list[EvidenceItem]:
        """Get evidence items from a specific agent."""
        return [i for i in self._items if i.agent_type == agent_type]

    def items_by_dimension(self, dimension: EvidenceDimension) -> list[EvidenceItem]:
        """Get evidence items for a specific dimension."""
        return [i for i in self._items if i.dimension == dimension]

    @property
    def all_values_with_sources(self) -> list[tuple[Decimal | None, str, str]]:
        """Get all (value, source_tool, source_url) tuples for audit."""
        return [(i.value, i.source_tool, i.source_url or "") for i in self._items]

    def validate(self) -> list[str]:
        """Validate the ledger and return a list of issues found."""
        issues = []
        for item in self._items:
            if not item.has_source:
                issues.append(f"Evidence item '{item.claim[:50]}' has no source tool")
            if item.value is not None and item.confidence < Decimal("0.50"):
                issues.append(f"Evidence item '{item.claim[:50]}' has low confidence: {item.confidence}")
            if item.is_expired:
                issues.append(f"Evidence item '{item.claim[:50]}' has expired data")
        return issues

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"EvidenceLedger(run_id={self.run_id}, items={len(self._items)})"
