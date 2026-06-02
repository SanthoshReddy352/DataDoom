"""FastAPI dependencies: app state, DB sessions, and (no-op local) auth.

Auth is a no-op dependency in local mode (08 §1); team mode swaps in a real
bearer-token dependency without changing any route signature.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from .state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.dd


def get_session(request: Request) -> Iterator[Session]:
    """Yield a transactional session for the request (commit/rollback handled)."""
    state: AppState = request.app.state.dd
    with state.db.session() as session:
        yield session


def current_owner() -> None:
    """No-op auth: local mode has a single implicit owner (``owner_id = None``)."""
    return None
