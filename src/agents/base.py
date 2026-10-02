"""Base ReAct agent factory — shared logic for all evidence agents."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from src.evidence.models import AgentType, EvidenceDimension, EvidenceItem


def _parse_evidence_from_response(
    response_text: str,
    run_id: str,
    candidate_id: str,
    agent_type: AgentType,
) -> list[EvidenceItem]:
    """Parse evidence items from an LLM response JSON."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        match = re.search(r'\{[\s\S]*\}', response_text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return []
        else:
            return []

    evidence_data = data.get("evidence", [])
    if not isinstance(evidence_data, list):
        return []

    items = []
    for e in evidence_data:
        try:
            dim = EvidenceDimension(e.get("dimension", ""))
        except ValueError:
            dim = EvidenceDimension.MARKET_DEMAND  # fallback

        items.append(EvidenceItem(
            run_id=run_id,
            candidate_id=candidate_id,
            agent_type=agent_type,
            dimension=dim,
            claim=e.get("claim", ""),
            value=Decimal(str(e.get("value", "0"))) if e.get("value") is not None else None,
            unit=e.get("unit"),
            source_tool=agent_type.value + "_agent",
            source_url=None,
            fetch_time=datetime.now(),
            confidence=Decimal(str(e.get("confidence", "0.80"))),
        ))

    return items


async def run_evidence_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    agent_type: AgentType,
    run_id: str,
    candidate_id: str,
    candidate_info: dict[str, Any],
) -> list[EvidenceItem]:
    """Run a ReAct evidence agent and return parsed evidence items.

    For the demo, this uses a simplified approach:
    1. Build a prompt with the candidate info
    2. Let the LLM decide which tools to call (or use mock responses)
    3. Parse the response into EvidenceItem objects
    """
    # Build the user prompt
    user_prompt = f"""Evaluate this product candidate:

Name: {candidate_info.get('name', 'Unknown')}
Category: {candidate_info.get('category', 'Unknown')}
Platform: {candidate_info.get('platform', 'Unknown')}
Source Country: {candidate_info.get('source_country', 'Unknown')}
Target Country: {candidate_info.get('target_country', 'Unknown')}
Price (USD): {candidate_info.get('price_usd', 'N/A')}
Weight (kg): {candidate_info.get('weight_kg', 'N/A')}
MOQ: {candidate_info.get('moq', 'N/A')}

Gather evidence and return your findings in the specified JSON format."""

    # Call the LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        response_text = response.content
    except Exception as e:
        # If LLM fails, return empty evidence with an error note
        return [EvidenceItem(
            run_id=run_id,
            candidate_id=candidate_id,
            agent_type=agent_type,
            dimension=EvidenceDimension.MARKET_DEMAND,
            claim=f"Agent failed: {str(e)[:100]}",
            value=None,
            source_tool="error",
            confidence=Decimal("0.0"),
        )]

    # Parse evidence from response
    items = _parse_evidence_from_response(response_text, run_id, candidate_id, agent_type)

    # If no items parsed, create a fallback from the raw response
    if not items:
        items = [EvidenceItem(
            run_id=run_id,
            candidate_id=candidate_id,
            agent_type=agent_type,
            dimension=EvidenceDimension.MARKET_DEMAND,
            claim=f"Agent completed but produced unstructured output: {response_text[:200]}",
            value=None,
            source_tool=agent_type.value + "_agent",
            confidence=Decimal("0.30"),
        )]

    return items
