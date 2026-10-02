"""FastAPI application entrypoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.api.schemas import HealthResponse
from src.config.settings import settings

app = FastAPI(
    title=settings.app_name,
    description="Multi-agent product selection decision system for cross-border e-commerce",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (allow all for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now().isoformat(),
    )


@app.on_event("startup")
async def startup():
    """Application startup — log configuration."""
    print(f"🚀 {settings.app_name} v0.1.0 starting...")
    print(f"   LLM Provider: {settings.llm_provider}")
    print(f"   Embedding Provider: {settings.embedding_provider}")
    print(f"   Reranker Provider: {settings.reranker_provider}")
    print(f"   Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    print(f"   Redis: {settings.redis_host}:{settings.redis_port}")
    print(f"   Milvus: {settings.milvus_host}:{settings.milvus_port}")
