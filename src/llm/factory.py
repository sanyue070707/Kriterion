"""LLM factory — Qwen3-Max or Mock LLM based on configuration."""

from __future__ import annotations

import json
import random
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

from src.config.settings import settings


class MockChatModel(BaseChatModel):
    """Simulated LLM for demo without API key.

    Returns plausible structured responses based on the prompt content.
    """

    model_name: str = "mock-llm"

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> Any:
        from langchain_core.outputs import ChatGeneration, ChatResult

        last_msg = messages[-1].content if messages else ""

        # Try to detect what kind of response is expected
        if "decision" in last_msg.lower() or "verdict" in last_msg.lower():
            text = self._mock_decision_response()
        elif "trend" in last_msg.lower() or "demand" in last_msg.lower():
            text = self._mock_trend_response()
        elif "cost" in last_msg.lower() or "margin" in last_msg.lower() or "freight" in last_msg.lower():
            text = self._mock_cost_response()
        elif "compliance" in last_msg.lower() or "trademark" in last_msg.lower() or "risk" in last_msg.lower():
            text = self._mock_compliance_response()
        else:
            text = self._mock_generic_response()

        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    async def _agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> Any:
        return self._generate(messages, **kwargs)

    def _mock_trend_response(self) -> str:
        return json.dumps({
            "evidence": [
                {"dimension": "market_demand", "claim": "Search volume is 85,000/month", "value": 85000, "unit": "searches/month", "confidence": 0.85},
                {"dimension": "trend_momentum", "claim": "Category growing at 22% YoY", "value": 22, "unit": "%", "confidence": 0.80},
                {"dimension": "competition", "claim": "12 active creator-sellers in category", "value": 12, "unit": "sellers", "confidence": 0.75},
                {"dimension": "influencer_activity", "claim": "28 influencer mentions this month", "value": 28, "unit": "mentions", "confidence": 0.70},
            ]
        })

    def _mock_cost_response(self) -> str:
        return json.dumps({
            "evidence": [
                {"dimension": "product_cost", "claim": "Supplier unit cost is $8.50", "value": 8.50, "unit": "USD", "confidence": 0.90},
                {"dimension": "freight_cost", "claim": "Sea freight cost is $1.20/kg", "value": 1.20, "unit": "USD/kg", "confidence": 0.85},
                {"dimension": "gross_margin", "claim": "Gross margin is 35.2%", "value": 35.2, "unit": "%", "confidence": 0.80},
                {"dimension": "net_margin", "claim": "Net margin is 18.5%", "value": 18.5, "unit": "%", "confidence": 0.75},
                {"dimension": "supply_stability", "claim": "3 suppliers available with 15-day lead time", "value": 3, "unit": "suppliers", "confidence": 0.70},
            ]
        })

    def _mock_compliance_response(self) -> str:
        return json.dumps({
            "evidence": [
                {"dimension": "trademark_risk", "claim": "No trademark conflicts found", "value": 0, "unit": "conflicts", "confidence": 0.85},
                {"dimension": "certification_gap", "claim": "FDA certification required for US market", "value": 1, "unit": "gaps", "confidence": 0.90},
                {"dimension": "compliance_warn", "claim": "Ingredient labeling requirements apply", "value": 1, "unit": "warnings", "confidence": 0.75},
                {"dimension": "import_duty", "claim": "Import duty is 5.3%", "value": 5.3, "unit": "%", "confidence": 0.80},
            ]
        })

    def _mock_decision_response(self) -> str:
        scores = {
            "market_demand": round(random.uniform(5.5, 8.5), 1),
            "competition": round(random.uniform(4.0, 7.0), 1),
            "cost_margin": round(random.uniform(5.0, 8.0), 1),
            "compliance_risk": round(random.uniform(6.0, 9.0), 1),
            "supply_stability": round(random.uniform(5.0, 7.5), 1),
            "trend_momentum": round(random.uniform(5.0, 8.0), 1),
            "return_rate": round(random.uniform(6.0, 9.0), 1),
        }
        overall = round(sum(scores.values()) / 7, 2)
        verdict = "go" if overall >= 7 else "watch" if overall >= 4 else "no_go"
        return json.dumps({
            "verdict": verdict,
            "verdict_reason": f"Overall score {overall}, {'strong candidate' if verdict == 'go' else 'moderate risk' if verdict == 'watch' else 'high risk'}",
            "scores": scores,
            "overall_score": overall,
            "evidence_summary": {"trend_demand": "Market favorable", "supply_cost": "Margin adequate", "compliance_risk": "Minor warnings"},
            "risk_flags": {},
            "watch_reasons": {} if verdict != "watch" else {"margin": "Monitor margin stability"},
        })

    def _mock_generic_response(self) -> str:
        return json.dumps({"status": "ok", "message": "Mock LLM response"})


def get_llm() -> BaseChatModel:
    """Factory: get LLM based on settings."""
    if settings.llm_provider == "qwen" and settings.qwen_api_key:
        return ChatOpenAI(
            model=settings.qwen_model_name,
            api_key=settings.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.1,
        )
    return MockChatModel()
