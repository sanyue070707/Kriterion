"""LLM factory.

The default provider is a deterministic local model, so the system runs with no
API key and nothing to download. Responses are selected by an explicit *role*
supplied at the call site - never by sniffing keywords out of the prompt, which
is brittle.

The decision-review node is the only place an LLM is used: it renders a
grounded narrative over numbers that were computed deterministically. Swap in
a real model (the `real-llm` extra) to replace the renderer with a genuine
`with_structured_output(...)` call.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.config.settings import settings


class MockChatModel(BaseChatModel):
    """Deterministic local stand-in for a chat model.

    Dispatch is by `role` (construction-time), so each call site gets the
    response shape it expects without fragile prompt matching.
    """

    role: str = "generic"
    model_name: str = "mock-llm"

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        text = self._render(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return self._generate(messages, **kwargs)

    # ── Dispatch ──

    def _render(self, messages: list[BaseMessage]) -> str:
        renderer = getattr(self, f"_render_{self.role}", None) or self._render_generic
        return renderer(messages)

    @staticmethod
    def _last_facts(messages: list[BaseMessage]) -> dict:
        """Extract the ground-truth facts dict the caller passed in."""
        for message in reversed(messages):
            content = message.content if isinstance(message.content, str) else ""
            try:
                payload = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, dict) and "facts" in payload:
                return payload["facts"]
        return {}

    # ── Roles ──

    def _render_decision_review(self, messages: list[BaseMessage]) -> str:
        """Render a grounded narrative over deterministically-computed facts.

        Only narrative fields are produced here; the caller ignores any numbers
        the model returns, so the model cannot drift the decision.
        """
        facts = self._last_facts(messages)
        verdict = facts.get("verdict", "watch")
        overall = facts.get("overall_score", 0.0)
        scores: dict = facts.get("scores", {})
        highlights: list = facts.get("evidence_highlights", [])
        watch_reasons: dict = facts.get("watch_reasons", {})

        strongest = max(scores, key=scores.get) if scores else "n/a"
        weakest = min(scores, key=scores.get) if scores else "n/a"

        if verdict == "go":
            headline = f"Recommend GO - weighted score {overall}/10 with no blocking compliance or margin issues."
        elif verdict == "no_go":
            headline = f"Recommend NO-GO - weighted score {overall}/10 fails the listing bar."
        else:
            headline = f"Recommend WATCH - weighted score {overall}/10 needs conditions to be met before launch."

        narrative = (
            f"{headline} Strongest signal is {strongest} ({scores.get(strongest, 'n/a')}); "
            f"weakest is {weakest} ({scores.get(weakest, 'n/a')}). "
            f"Findings are drawn from {len(highlights)} sourced evidence items collected by the "
            f"trend/demand, supply/cost, and compliance/risk agents."
        )
        if watch_reasons:
            narrative += " Open items: " + "; ".join(str(v) for v in watch_reasons.values()) + "."

        return json.dumps({
            "verdict_reason": headline,
            "evidence_summary": {"highlights": highlights},
            "watch_reasons": watch_reasons,
            "narrative": narrative,
        }, ensure_ascii=False)

    def _render_generic(self, messages: list[BaseMessage]) -> str:
        return json.dumps({"status": "ok"})


def get_llm(role: str = "generic") -> BaseChatModel:
    """Return a chat model for the given role.

    Defaults to the local deterministic model. Setting `llm_provider=real` with a
    real OpenAI-compatible endpoint (requires the `real-llm` extra).
    """
    if settings.llm_provider == "real" and settings.llm_api_key:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "llm_provider=real requires the 'real-llm' extra: pip install -e '.[real-llm]'"
            ) from exc
        return ChatOpenAI(
            model=settings.llm_model_name or "gpt-4o-mini",
            api_key=settings.llm_api_key,
            temperature=0.1,
        )
    return MockChatModel(role=role)
