"""LangGraph workflow assembly and compilation.

Flow:
  START → normalize → screen → [conditional]
    ├─ rejected → END
    └─ passed → fan_out → [parallel fan-out]
         ├─ collect_evidence_trend    ─┐
         ├─ collect_evidence_supply   ─┤→ gatekeep → review → output → END
         └─ collect_evidence_compliance┘
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    collect_evidence_compliance_node,
    collect_evidence_supply_node,
    collect_evidence_trend_node,
    fan_out_node,
    gatekeep_node,
    normalize_node,
    output_node,
    review_node,
    screen_node,
)
from src.graph.state import WorkflowState


def route_after_screen(state: WorkflowState) -> str:
    """Conditional edge: after screening, go to fan_out or END."""
    if state.get("screening_passed", False):
        return "fan_out"
    return "end_rejected"


def build_workflow() -> StateGraph:
    """Build and compile the evaluation workflow graph."""
    g = StateGraph(WorkflowState)

    # ── Add nodes ──
    g.add_node("normalize", normalize_node)
    g.add_node("screen", screen_node)
    g.add_node("fan_out", fan_out_node)
    g.add_node("collect_evidence_trend", collect_evidence_trend_node)
    g.add_node("collect_evidence_supply", collect_evidence_supply_node)
    g.add_node("collect_evidence_compliance", collect_evidence_compliance_node)
    g.add_node("gatekeep", gatekeep_node)
    g.add_node("review", review_node)
    g.add_node("output", output_node)

    # ── Linear: START → normalize → screen ──
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "screen")

    # ── Conditional: screen → fan_out or END ──
    g.add_conditional_edges(
        "screen",
        route_after_screen,
        {
            "fan_out": "fan_out",
            "end_rejected": END,
        },
    )

    # ── Parallel fan-out: fan_out → all 3 evidence agents ──
    g.add_edge("fan_out", "collect_evidence_trend")
    g.add_edge("fan_out", "collect_evidence_supply")
    g.add_edge("fan_out", "collect_evidence_compliance")

    # ── Barrier: all 3 evidence agents → gatekeep ──
    g.add_edge("collect_evidence_trend", "gatekeep")
    g.add_edge("collect_evidence_supply", "gatekeep")
    g.add_edge("collect_evidence_compliance", "gatekeep")

    # ── Linear: gatekeep → review → output → END ──
    g.add_edge("gatekeep", "review")
    g.add_edge("review", "output")
    g.add_edge("output", END)

    return g


def compile_workflow():
    """Compile the workflow graph for execution."""
    graph = build_workflow()
    return graph.compile()


# Singleton compiled graph
_workflow = None


def get_workflow():
    """Get or create the compiled workflow singleton."""
    global _workflow
    if _workflow is None:
        _workflow = compile_workflow()
    return _workflow
