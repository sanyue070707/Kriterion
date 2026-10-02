"""SSE streaming endpoint for workflow progress."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from src.graph.progress import emitter

router = APIRouter(prefix="/workflow", tags=["stream"])


@router.get("/{run_id}/stream")
async def workflow_stream(run_id: str, request: Request):
    """Stream workflow progress events via Server-Sent Events (SSE).

    The client connects and receives events as the workflow progresses:
    - node: which node is executing
    - status: started / completed / error
    - detail: optional extra info
    - ts: timestamp
    """
    async def event_generator():
        """Generate SSE events from Redis pub/sub."""
        try:
            pubsub = emitter.subscribe(run_id)
        except Exception:
            # Redis unavailable — send a single error event and stop
            yield {
                "event": "error",
                "data": json.dumps({"message": "Redis unavailable, SSE not supported"}),
            }
            return

        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({"run_id": run_id, "message": "SSE connected"}),
        }

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Get message from Redis (with timeout)
                message = pubsub.get_message(timeout=2.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, str):
                        yield {
                            "event": "progress",
                            "data": data,
                        }

                        # Check if this is a terminal event
                        try:
                            parsed = json.loads(data)
                            if parsed.get("node") == "output" and parsed.get("status") == "completed":
                                yield {
                                    "event": "done",
                                    "data": json.dumps({"run_id": run_id, "status": "completed"}),
                                }
                                break
                        except json.JSONDecodeError:
                            pass

                await asyncio.sleep(0.1)
        finally:
            try:
                pubsub.unsubscribe()
            except Exception:
                pass

    return EventSourceResponse(event_generator())
