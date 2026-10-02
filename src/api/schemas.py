"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Candidates ──

class CandidateCreate(BaseModel):
    name: str
    category: str
    subcategory: str | None = None
    platform: str
    source_country: str
    target_country: str
    price_usd: float | None = None
    currency: str = "USD"
    moq: int | None = None
    weight_kg: float | None = None
    metadata: dict[str, Any] | None = None


class CandidateResponse(BaseModel):
    id: str
    name: str
    category: str
    subcategory: str | None
    platform: str
    source_country: str
    target_country: str
    price_usd: float | None
    moq: int | None
    weight_kg: float | None
    status: str
    created_at: str


class CandidateListResponse(BaseModel):
    items: list[CandidateResponse]
    total: int


# ── Workflow ──

class WorkflowRunRequest(BaseModel):
    candidate_id: str


class WorkflowRunResponse(BaseModel):
    run_id: str
    candidate_id: str
    status: str


class WorkflowStatusResponse(BaseModel):
    run_id: str
    status: str
    current_node: str | None
    progress: list[dict[str, Any]]
    error_message: str | None


# ── Decision Cards ──

class DecisionCardResponse(BaseModel):
    id: str
    run_id: str
    candidate_id: str
    verdict: str
    scores: dict[str, float]
    overall_score: float
    unit_economics: dict | None
    evidence_summary: dict | None
    risk_flags: dict | None
    watch_reasons: dict | None
    decided_at: str


class DecisionCardListResponse(BaseModel):
    items: list[DecisionCardResponse]
    total: int


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
