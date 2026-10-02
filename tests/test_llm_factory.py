"""Tests for role-based LLM dispatch."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.factory import MockChatModel, get_llm


async def test_decision_review_role_renders_grounded_narrative():
    llm = get_llm(role="decision_review")
    facts = {
        "verdict": "go",
        "overall_score": 7.6,
        "scores": {"cost_margin": 8.0, "compliance_risk": 9.0},
        "evidence_highlights": ["a", "b"],
        "watch_reasons": {},
    }
    payload = HumanMessage(content=json.dumps({"role": "decision_review", "facts": facts}))
    response = await llm.ainvoke([SystemMessage(content="system"), payload])
    data = json.loads(response.content)

    assert "GO" in data["verdict_reason"]
    assert "cost_margin" in data["narrative"]
    assert data["evidence_summary"]["highlights"] == ["a", "b"]


async def test_generic_role_is_a_noop_status():
    llm = get_llm()  # default role
    response = await llm.ainvoke([HumanMessage(content="anything at all")])
    assert json.loads(response.content) == {"status": "ok"}


def test_get_llm_is_deterministic_and_local():
    assert isinstance(get_llm(role="decision_review"), MockChatModel)
    a = get_llm(role="decision_review")
    b = get_llm(role="decision_review")
    assert a.role == b.role == "decision_review"
