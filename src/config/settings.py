"""Application settings.

Everything runs locally against SQLite: no external services, no API keys.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──
    app_name: str = "Kriterion"
    debug: bool = False

    # ── LLM ──
    # "mock" (default, no API key) | "real" (requires the `real-llm` extra)
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model_name: str = ""

    # ── Database (local SQLite, auto-created) ──
    database_url: str = "sqlite+aiosqlite:///./kriterion.db"

    # ── Startup bootstrap ──
    data_dir: str = "data"
    auto_bootstrap: bool = True

    # ── Screening defaults (methodology constants) ──
    min_viable_margin_tiktok: float = 15.0  # %
    min_viable_margin_shopee: float = 12.0  # %
    max_price_usd: float = 500.0
    min_price_usd: float = 1.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
