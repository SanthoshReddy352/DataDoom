"""Progress fan-out: engine ``ProgressEmitter`` -> WebSocket hub (08 §7).

The :class:`EventHub` is an in-process async pub/sub keyed by ``run_id``. The
worker thread publishes events; the API's WebSocket/SSE handlers subscribe. The
hub keeps a per-run **replay buffer** so a late subscriber (the browser opening
the tracker after the run started) receives the stages so far, then live updates.

Cross-thread safety: the worker runs in a thread pool, so ``publish`` marshals
queue writes onto the API event loop via ``call_soon_threadsafe``. With no loop
registered (library/test use) it still records history and serves replay.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import AsyncIterator
from typing import Any

from datadoom.engine.progress import ProgressEmitter

# Canonical pipeline stages (08 §7 / 03 §4). Optional stages appear only when the
# spec enables them; in P1 the engine emits the headless subset.
CANONICAL_STAGES = (
    "intake",
    "snapshot",
    "seed",
    "base_generation",
    "causal",
    "failure_injection",
    "difficulty",
    "compliance",
    "packaging",
)


class RunCancelled(Exception):
    """Raised inside the pipeline when a cooperative cancel was requested."""


Event = dict[str, Any]


class EventHub:
    """Per-run pub/sub with replay. One instance per server process."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = {}
        self._history: dict[str, list[Event]] = {}
        self._terminal: dict[str, bool] = {}
        self._cancels: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # --- loop wiring (called once by the API on startup) --------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # --- cancellation -------------------------------------------------------------
    def cancel_flag(self, run_id: str) -> threading.Event:
        with self._lock:
            return self._cancels.setdefault(run_id, threading.Event())

    def request_cancel(self, run_id: str) -> None:
        self.cancel_flag(run_id).set()

    def is_cancelled(self, run_id: str) -> bool:
        return self.cancel_flag(run_id).is_set()

    # --- publishing ---------------------------------------------------------------
    def publish(self, run_id: str, event: Event) -> None:
        with self._lock:
            self._history.setdefault(run_id, []).append(event)
            if event.get("type") in {"completed", "failed", "cancelled"}:
                self._terminal[run_id] = True
            queues = list(self._subscribers.get(run_id, ()))
        for q in queues:
            self._enqueue(q, event)

    def _enqueue(self, q: asyncio.Queue[Event], event: Event) -> None:
        loop = self._loop
        if loop is None:
            # No API loop (library/test); history still records for replay.
            return
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(q.put_nowait, event)

    # --- subscription -------------------------------------------------------------
    async def subscribe(self, run_id: str) -> AsyncIterator[Event]:
        """Yield replay of events so far, then live events until a terminal one."""
        q: asyncio.Queue[Event] = asyncio.Queue()
        with self._lock:
            replay = list(self._history.get(run_id, ()))
            already_terminal = self._terminal.get(run_id, False)
            self._subscribers.setdefault(run_id, set()).add(q)
        try:
            for ev in replay:
                yield ev
            if already_terminal:
                return
            while True:
                ev = await q.get()
                yield ev
                if ev.get("type") in {"completed", "failed", "cancelled"}:
                    return
        finally:
            with self._lock:
                subs = self._subscribers.get(run_id)
                if subs is not None:
                    subs.discard(q)

    def history(self, run_id: str) -> list[Event]:
        with self._lock:
            return list(self._history.get(run_id, ()))


class HubProgressEmitter(ProgressEmitter):
    """Engine progress sink that republishes to an :class:`EventHub`.

    Translates the engine's per-stage ``emit(stage, pct, message)`` calls into the
    WS event shapes of 08 §7, synthesizing a ``done`` for the previous stage when
    a new one begins, and checking the cooperative cancel flag at every boundary.
    """

    def __init__(self, hub: EventHub, run_id: str) -> None:
        self.hub = hub
        self.run_id = run_id
        self._prev_stage: str | None = None

    def emit(self, stage: str, pct: int, message: str = "") -> None:
        if self.hub.is_cancelled(self.run_id):
            raise RunCancelled(stage)
        if self._prev_stage is not None and self._prev_stage != stage:
            self.hub.publish(
                self.run_id,
                {"type": "stage", "stage": self._prev_stage, "status": "done", "pct": pct},
            )
        self.hub.publish(
            self.run_id,
            {"type": "stage", "stage": stage, "status": "running", "pct": pct},
        )
        if message:
            self.hub.publish(
                self.run_id, {"type": "log", "level": "info", "message": message}
            )
        self._prev_stage = stage

    def finish(self, pct: int = 100) -> None:
        """Mark the final stage done once the pipeline returns."""
        if self._prev_stage is not None:
            self.hub.publish(
                self.run_id,
                {"type": "stage", "stage": self._prev_stage, "status": "done", "pct": pct},
            )
