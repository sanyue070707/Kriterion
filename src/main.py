"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.api.router import api_router
from src.api.schemas import HealthResponse
from src.config.settings import settings

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare data/schema/seed/indexes on startup (idempotent)."""
    if settings.auto_bootstrap:
        from src.bootstrap import bootstrap

        await bootstrap(verbose=False)
    else:
        from src.db.connection import init_db

        await init_db()
    print(f"[Kriterion] ready - LLM provider: {settings.llm_provider}")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Multi-agent product selection decision system for cross-border e-commerce",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the single-page web UI."""
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0", timestamp=datetime.now().isoformat())
