"""Command-line entry point.

    kriterion bootstrap            prepare data / schema / indexes
    kriterion demo [--candidate X] run one evaluation and print the decision card
    kriterion web  [--port 8000]   start the web UI
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from src.console import enable_safe_output
from src.service.evaluate import EvalResult, candidate_to_raw, run_evaluation

VERDICT_LABEL = {"go": "GO", "watch": "WATCH", "no_go": "NO-GO"}


def _bar(score: float, width: int = 10) -> str:
    filled = max(0, min(width, int(round(score))))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


async def _resolve_candidate(session, ref: str | None):
    from src.db.repository import get_candidate, list_candidates

    if ref:
        try:
            c = await get_candidate(session, uuid.UUID(ref))
            if c:
                return c
        except ValueError:
            pass
        for c in await list_candidates(session, limit=1000):
            if ref.lower() in c.name.lower():
                return c
        raise SystemExit(f"No candidate matched {ref!r}")

    candidates = await list_candidates(session, limit=1000)
    if not candidates:
        raise SystemExit("No candidates found — run `kriterion bootstrap` first.")
    for c in candidates:
        if c.name.startswith("Sample: Clear"):
            return c
    return candidates[0]


def _render(result: EvalResult) -> None:
    line = "=" * 68
    print(f"\n{line}\n  DECISION CARD\n{line}")
    print(f"  Candidate: {result.candidate_name}")
    print(f"  Run ID:    {result.run_id}")

    if not result.screening_passed:
        print(f"\n  REJECTED AT SCREENING: {result.screening_reason}")
        print(f"{line}\n")
        return

    card = result.decision_card
    if card is None:
        print("  No decision card produced.")
        return

    print(f"  Verdict:   {VERDICT_LABEL.get(card.verdict, card.verdict)}  (score {card.overall_score}/10)")
    print(f"  Reason:    {card.verdict_reason}")

    print("\n  Dimension scores:")
    for dim, score in card.scores.items():
        print(f"    {dim:<18} {_bar(score)} {score}")

    if card.unit_economics:
        ue = card.unit_economics
        print("\n  Unit economics:")
        print(f"    retail ${ue['retail_price']}  product ${ue['product_cost']}  freight ${ue['freight_cost']}")
        print(f"    gross margin {ue['gross_margin_pct']}%   net margin {ue['net_margin_pct']}%")

    if card.risk_flags:
        print("\n  Risk flags:")
        for flag, severity in card.risk_flags.items():
            print(f"    [{severity}] {flag}")
    if card.watch_reasons:
        print("\n  Watch reasons:")
        for reason in card.watch_reasons.values():
            print(f"    - {reason}")

    summary = card.evidence_summary or {}
    if summary.get("narrative"):
        print(f"\n  Narrative: {summary['narrative']}")

    report = result.gatekeeper_report or {}
    print(
        f"\n  Gatekeeper: {report.get('valid_items', 0)} valid / "
        f"{report.get('stripped_items', 0)} stripped / "
        f"{report.get('low_confidence_items', 0)} low-confidence"
    )

    print(f"\n  Evidence ledger ({len(result.gated_evidence)} items):")
    for e in result.gated_evidence:
        value = "" if e.value is None else f" = {e.value}{(' ' + e.unit) if e.unit else ''}"
        print(f"    [{e.dimension.value}] {e.claim}{value}")
        print(f"        source={e.source_tool}  url={e.source_url}  conf={e.confidence}")

    print(f"\n  Tool calls ({len(result.tool_trace)}):")
    for call in result.tool_trace:
        status = "skip" if call["skipped"] else ("ok" if call["ok"] else "FAIL")
        print(f"    {status:<4} {call['tool']:<30} {call['elapsed_ms']}ms")
    print(f"\n{line}\n")


async def _cmd_bootstrap() -> None:
    from src.bootstrap import bootstrap

    print("Bootstrapping...")
    await bootstrap(verbose=True)
    print("Ready.")


async def _cmd_demo(ref: str | None) -> None:
    from src.bootstrap import bootstrap
    from src.db.connection import async_session_factory

    print("Bootstrapping...")
    await bootstrap(verbose=True)

    async with async_session_factory() as session:
        candidate = await _resolve_candidate(session, ref)
        candidate_raw = candidate_to_raw(candidate)

    print(f"\nEvaluating: {candidate_raw['name']}")
    result = await run_evaluation(candidate_raw)
    _render(result)


def _cmd_web(host: str, port: int) -> None:
    import uvicorn

    print(f"Starting web UI on http://{host}:{port}  (Ctrl+C to stop)")
    uvicorn.run("src.main:app", host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    enable_safe_output()

    parser = argparse.ArgumentParser(
        prog="kriterion", description="Multi-agent product selection decision system"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("bootstrap", help="prepare data, schema, indexes, sample candidates")

    demo = sub.add_parser("demo", help="run one evaluation and print the decision card")
    demo.add_argument("--candidate", default=None, help="candidate id, name substring, or leave blank")

    web = sub.add_parser("web", help="start the web UI")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        asyncio.run(_cmd_bootstrap())
    elif args.command == "demo":
        asyncio.run(_cmd_demo(args.candidate))
    elif args.command == "web":
        _cmd_web(args.host, args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
