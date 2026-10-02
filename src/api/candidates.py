"""Candidates API endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import CandidateCreate, CandidateListResponse, CandidateResponse
from src.db.connection import get_session
from src.db.repository import create_candidate, get_candidate, list_candidates

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateResponse, status_code=201)
async def create_candidate_endpoint(
    body: CandidateCreate,
    session: AsyncSession = Depends(get_session),
):
    """Submit a new product candidate for evaluation."""
    from src.db.repository import create_candidate as _create

    c = await _create(
        session,
        name=body.name,
        category=body.category,
        subcategory=body.subcategory,
        platform=body.platform,
        source_country=body.source_country,
        target_country=body.target_country,
        price_usd=body.price_usd,
        currency=body.currency,
        moq=body.moq,
        weight_kg=body.weight_kg,
        metadata_=body.metadata or {},
    )
    return CandidateResponse(
        id=str(c.id),
        name=c.name,
        category=c.category,
        subcategory=c.subcategory,
        platform=c.platform,
        source_country=c.source_country,
        target_country=c.target_country,
        price_usd=float(c.price_usd) if c.price_usd else None,
        moq=c.moq,
        weight_kg=float(c.weight_kg) if c.weight_kg else None,
        status=c.status,
        created_at=c.created_at.isoformat(),
    )


@router.get("", response_model=CandidateListResponse)
async def list_candidates_endpoint(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """List product candidates."""
    candidates = await list_candidates(session, limit=limit, offset=offset)
    items = [
        CandidateResponse(
            id=str(c.id),
            name=c.name,
            category=c.category,
            subcategory=c.subcategory,
            platform=c.platform,
            source_country=c.source_country,
            target_country=c.target_country,
            price_usd=float(c.price_usd) if c.price_usd else None,
            moq=c.moq,
            weight_kg=float(c.weight_kg) if c.weight_kg else None,
            status=c.status,
            created_at=c.created_at.isoformat(),
        )
        for c in candidates
    ]
    return CandidateListResponse(items=items, total=len(items))


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate_endpoint(
    candidate_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific candidate by ID."""
    c = await get_candidate(session, uuid.UUID(candidate_id))
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateResponse(
        id=str(c.id),
        name=c.name,
        category=c.category,
        subcategory=c.subcategory,
        platform=c.platform,
        source_country=c.source_country,
        target_country=c.target_country,
        price_usd=float(c.price_usd) if c.price_usd else None,
        moq=c.moq,
        weight_kg=float(c.weight_kg) if c.weight_kg else None,
        status=c.status,
        created_at=c.created_at.isoformat(),
    )
