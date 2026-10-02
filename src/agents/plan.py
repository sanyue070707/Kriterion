"""Evidence-plan executor.

Each evidence agent runs a declarative *plan*: an ordered list of rules, where
a rule names a business tool, builds its arguments from the candidate context,
and maps the tool's result into evidence payloads. The executor records a
`ToolCallRecord` for every call (name, args, latency, result/error/skip), giving
a complete trace of which data sources were consulted.

Tool selection is declarative, which keeps runs deterministic and reproducible.
`run_evidence_agent` in `base.py` is the single place to swap in a
model-driven loop.

Degradation is first-class: a rule whose arguments can't be satisfied (e.g.
unit economics with no supplier quote) raises `SkipStep`, which is recorded as
a skipped call and, when the rule is not optional, surfaced as a low-confidence
"gap" evidence item instead of silently disappearing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any

from langchain_core.tools import BaseTool

from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem

DEFAULT_TTL_DAYS = 7.0


class SkipStep(Exception):
    """Raised by an argument builder to skip an inapplicable step."""


@dataclass
class ToolCallRecord:
    """One recorded tool invocation (or a deliberate skip)."""

    tool: str
    args: dict
    ok: bool
    skipped: bool
    elapsed_ms: int
    result: dict | None = None
    error: str | None = None
    source_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "ok": self.ok,
            "skipped": self.skipped,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "source_url": self.source_url,
        }


@dataclass
class PlanContext:
    """Mutable state threaded through a plan run."""

    agent_type: AgentType
    run_id: str
    candidate_id: str
    candidate: dict
    facts: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    """A single step: call `tool` with `args`, then `emit` evidence payloads."""

    tool: BaseTool
    primary_dimension: EvidenceDimension
    args: Callable[[PlanContext], dict]
    emit: Callable[[dict, PlanContext], list[dict]]
    apply: Callable[[dict, PlanContext], None] | None = None
    ttl_days: float = DEFAULT_TTL_DAYS
    optional: bool = False


def _compact(result: Any, max_items: int = 3) -> Any:
    """Trim long lists so `raw_response` stays auditable but small."""
    if isinstance(result, dict):
        compacted = {}
        for key, value in result.items():
            if isinstance(value, list) and len(value) > max_items:
                compacted[key] = value[:max_items] + [f"... (+{len(value) - max_items} more)"]
            else:
                compacted[key] = value
        return compacted
    return result


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_time(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now()


async def run_plan(plan: list[Rule], context: PlanContext) -> list[EvidenceItem]:
    """Execute a plan and return the evidence it produced."""
    items: list[EvidenceItem] = []

    for rule in plan:
        # 1. Build arguments — may deliberately skip this step.
        try:
            args = rule.args(context)
        except SkipStep as exc:
            context.tool_calls.append(
                ToolCallRecord(
                    tool=rule.tool.name, args={}, ok=False, skipped=True,
                    elapsed_ms=0, error=str(exc) or "skipped",
                )
            )
            if not rule.optional:
                items.append(_degradation_item(context, rule, str(exc) or "step skipped"))
            continue

        # 2. Call the tool, timing it and never letting it abort the plan.
        started = perf_counter()
        try:
            result = await rule.tool.ainvoke(args)
            ok, error = True, None
        except Exception as exc:  # noqa: BLE001 - degradation is intentional
            result, ok, error = None, False, str(exc)[:200]
        elapsed_ms = int((perf_counter() - started) * 1000)

        context.tool_calls.append(
            ToolCallRecord(
                tool=rule.tool.name, args=args, ok=ok, skipped=False, elapsed_ms=elapsed_ms,
                result=_compact(result) if ok else None,
                error=error,
                source_url=(result or {}).get("source_url") if ok else None,
            )
        )

        if not ok:
            if not rule.optional:
                items.append(_degradation_item(context, rule, error or "tool failed"))
            continue

        # 3. Stash cross-step facts and emit evidence.
        if rule.apply is not None:
            rule.apply(result, context)

        payloads = rule.emit(result, context) or []
        for payload in payloads:
            items.append(_build_item(context, rule, result, payload))

    return items


def _build_item(context: PlanContext, rule: Rule, result: dict, payload: dict) -> EvidenceItem:
    """Turn an emitted payload + the tool result into a sourced evidence item."""
    now = datetime.now()
    return EvidenceItem(
        run_id=context.run_id,
        candidate_id=context.candidate_id,
        agent_type=context.agent_type,
        dimension=payload.get("dimension", rule.primary_dimension),
        claim=payload.get("claim", ""),
        value=_to_decimal(payload.get("value")),
        unit=payload.get("unit"),
        source_tool=rule.tool.name,
        source_url=result.get("source_url") or payload.get("source_url"),
        fetch_time=_parse_time(result.get("fetch_time")),
        validity_until=now + timedelta(days=rule.ttl_days),
        confidence=_to_decimal(payload.get("confidence")) or Decimal("0.80"),
        raw_response=payload.get("raw", _compact(result)),
    )


def _degradation_item(context: PlanContext, rule: Rule, note: str) -> EvidenceItem:
    """Evidence recording that a data source was unavailable (a visible gap)."""
    now = datetime.now()
    return EvidenceItem(
        run_id=context.run_id,
        candidate_id=context.candidate_id,
        agent_type=context.agent_type,
        dimension=rule.primary_dimension,
        claim=f"Data source unavailable via {rule.tool.name}: {note}",
        value=None,
        unit=None,
        source_tool=rule.tool.name,
        source_url=None,
        fetch_time=now,
        validity_until=None,  # a gap note is not data; it should not expire out
        confidence=Decimal("0.20"),
        raw_response={"degraded": True, "note": note},
    )
