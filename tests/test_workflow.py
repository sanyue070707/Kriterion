"""Tests for LangGraph workflow graph structure."""

from src.graph.workflow import build_workflow, compile_workflow


class TestWorkflow:
    def test_build_workflow(self):
        """Test that the workflow graph can be built without errors."""
        graph = build_workflow()
        assert graph is not None

    def test_compile_workflow(self):
        """Test that the workflow graph can be compiled."""
        compiled = compile_workflow()
        assert compiled is not None

    def test_workflow_nodes_exist(self):
        """Test that all expected nodes are in the graph."""
        graph = build_workflow()
        expected_nodes = {
            "normalize", "screen", "fan_out",
            "collect_evidence_trend", "collect_evidence_supply", "collect_evidence_compliance",
            "gatekeep", "review", "output",
        }
        # LangGraph stores nodes internally
        assert expected_nodes.issubset(set(graph.nodes.keys()))
