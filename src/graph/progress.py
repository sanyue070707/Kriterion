"""Redis-based progress emitter for SSE streaming."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import redis

from src.config.settings import settings


class ProgressEmitter:
    """Publish workflow progress events to Redis for SSE consumption."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
            )
        return self._redis

    def emit(self, run_id: str, node: str, status: str, detail: str | None = None) -> None:
        """Emit a progress event to the run's Redis channel."""
        try:
            r = self._get_redis()
            event = {
                "run_id": run_id,
                "node": node,
                "status": status,
                "detail": detail,
                "ts": datetime.now().isoformat(),
            }
            r.publish(f"workflow:{run_id}", json.dumps(event))
        except Exception:
            # Redis unavailable — silently skip (demo-friendly)
            pass

    def subscribe(self, run_id: str):
        """Subscribe to a run's progress channel. Returns a PubSub object."""
        r = self._get_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(f"workflow:{run_id}")
        return pubsub


# Singleton
emitter = ProgressEmitter()
