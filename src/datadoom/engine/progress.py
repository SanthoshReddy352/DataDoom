"""Progress emission contract.

The engine stays framework-free: it emits stage events to a sink. In P0 the sink
is a no-op; later phases wire a WebSocket hub behind the same interface.
"""

from __future__ import annotations


class ProgressEmitter:
    """No-op progress sink. Subclasses publish events elsewhere."""

    def emit(self, stage: str, pct: int, message: str = "") -> None:  # noqa: D401
        return None
