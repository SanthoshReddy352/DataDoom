"""Live progress transport (08 §7): WebSocket primary, SSE fallback.

Both subscribe to the :class:`~datadoom.jobs.progress.EventHub`, which replays
the stage events so far to a late subscriber, then streams live updates until a
terminal event (``completed`` / ``failed`` / ``cancelled``). The WS channel also
accepts ``{"type":"cancel"}`` from the client.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from .state import AppState

router = APIRouter(tags=["ws"])

_TERMINAL = {"completed", "failed", "cancelled"}


@router.websocket("/api/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.dd
    hub = state.hub

    async def pump_client() -> None:
        # Listen for client -> server messages (only "cancel" is meaningful).
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    data = json.loads(msg)
                except ValueError:
                    continue
                if data.get("type") == "cancel":
                    hub.request_cancel(run_id)
        except WebSocketDisconnect:
            return

    client_task = asyncio.create_task(pump_client())
    try:
        async for event in hub.subscribe(run_id):
            await websocket.send_json(event)
            if event.get("type") in _TERMINAL:
                break
    except WebSocketDisconnect:
        pass
    finally:
        client_task.cancel()
        with contextlib.suppress(RuntimeError):
            await websocket.close()


@router.get("/api/runs/{run_id}/events")
async def sse_run(run_id: str, request: Request) -> StreamingResponse:
    state: AppState = request.app.state.dd
    hub = state.hub

    async def event_stream():  # noqa: ANN202
        async for event in hub.subscribe(run_id):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in _TERMINAL:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
