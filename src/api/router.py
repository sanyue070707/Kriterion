"""Top-level API router — aggregates all sub-routers."""

from fastapi import APIRouter

from src.api.candidates import router as candidates_router
from src.api.decisions import router as decisions_router
from src.api.stream import router as stream_router
from src.api.workflow import router as workflow_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(candidates_router)
api_router.include_router(decisions_router)
api_router.include_router(workflow_router)
api_router.include_router(stream_router)
