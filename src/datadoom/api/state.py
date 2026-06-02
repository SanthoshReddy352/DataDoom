"""Shared application state, assembled by the app factory and hung on
``app.state.dd``. Holds the singletons the routes need: config, the database,
the artifact store, the event hub, and the worker pool.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datadoom.config import Config
from datadoom.jobs import EventHub, WorkerPool
from datadoom.store import ArtifactStore, Database


@dataclass
class AppState:
    config: Config
    db: Database
    artifacts: ArtifactStore
    hub: EventHub
    worker: WorkerPool
    # In-process idempotency map: (dataset_id, key) -> run_id (08 §1). Sufficient
    # for the single-process local server; team mode would persist this.
    idempotency: dict[tuple[str, str], str] = field(default_factory=dict)
