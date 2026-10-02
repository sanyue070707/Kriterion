"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──
    app_name: str = "Kriterion"
    debug: bool = True

    # ── LLM ──
    llm_provider: str = "mock"  # "qwen" | "mock"
    qwen_api_key: str = ""
    qwen_model_name: str = "qwen-max"

    # ── Embedding & Reranker ──
    embedding_provider: str = "mock"  # "local" | "mock"
    reranker_provider: str = "mock"  # "local" | "mock"
    bge_m3_model: str = "BAAI/bge-m3"
    bge_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_dim: int = 1024  # BGE-M3 dense dimension

    # ── PostgreSQL ──
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "kriterion"
    postgres_user: str = "kriterion"
    postgres_password: str = "kriterion_dev"
    database_url: str = "postgresql+asyncpg://kriterion:kriterion_dev@localhost:5432/kriterion"

    # ── Redis ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379/0"

    # ── Milvus ──
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # ── Langfuse ──
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = False

    # ── Screening defaults ──
    min_viable_margin_tiktok: float = 15.0  # %
    min_viable_margin_shopee: float = 12.0  # %
    max_price_usd: float = 500.0
    min_price_usd: float = 1.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
