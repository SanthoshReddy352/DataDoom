"""Job execution layer (03 §3.3).

The default backend is an **in-process** thread-pool worker that drives
``engine.pipeline`` and fans out progress events to the WebSocket hub. It may
import ``engine`` and ``store`` but nothing from ``api``/``cli`` (the hub lives
here so ``api`` can subscribe without ``jobs`` reaching upward).
"""

from __future__ import annotations

from .progress import EventHub, HubProgressEmitter, RunCancelled
from .worker import WorkerPool

__all__ = ["EventHub", "HubProgressEmitter", "RunCancelled", "WorkerPool"]
