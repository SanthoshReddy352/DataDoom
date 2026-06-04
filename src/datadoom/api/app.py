"""FastAPI application factory (08, 17 step 9).

Assembles config -> store -> jobs -> api into one app: opens the DB (running
Alembic to head), wires the worker + event hub, mounts the REST routes and the
WebSocket/SSE transport, installs the error envelope, and serves the bundled SPA
from ``webdist/`` (so ``datadoom serve`` is a complete app with no Node needed).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from datadoom.config import Config, load_config
from datadoom.jobs import EventHub, WorkerPool
from datadoom.plugins import load_plugins
from datadoom.store import LocalArtifactStore, init_database
from datadoom.version import __version__

from . import ws
from .errors import install_error_handlers
from .routes import artifacts, datasets, meta, plugins, runs, specs, templates
from .state import AppState

WEBDIST = Path(__file__).resolve().parent.parent / "webdist"


def create_app(config: Config | None = None) -> FastAPI:
    config = config or load_config()
    config.ensure_dirs()

    # Discover plugins (entry points + local dir) into the engine's lookup tables;
    # conflicts fail loudly here rather than silently shadowing a capability (09 §3).
    load_plugins(local_dir=config.home / "plugins")

    db = init_database(config.db_url)
    artifact_store = LocalArtifactStore(config.artifacts_dir)
    hub = EventHub()
    worker = WorkerPool(db, artifact_store, hub, __version__)
    state = AppState(
        config=config, db=db, artifacts=artifact_store, hub=hub, worker=worker
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202
        # Bind the running loop so worker threads can marshal WS events onto it.
        hub.bind_loop(asyncio.get_running_loop())
        yield
        worker.shutdown()
        db.dispose()

    app = FastAPI(
        title="DataDoom",
        version=__version__,
        description="Local-first engine for controllable, reproducible synthetic data.",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.dd = state

    install_error_handlers(app)

    for module in (meta, specs, datasets, runs, artifacts, templates, plugins):
        app.include_router(module.router)
    app.include_router(ws.router)

    _mount_spa(app)
    return app


def _mount_spa(app: FastAPI) -> None:
    """Serve the built SPA at ``/`` with client-side-routing fallback.

    If ``webdist/`` is absent (dev before the frontend is built), ``/`` returns a
    friendly JSON pointer instead of 404 so the API is still usable.
    """
    if not (WEBDIST / "index.html").exists():

        @app.get("/", include_in_schema=False)
        async def _no_spa() -> JSONResponse:  # noqa: ANN202
            return JSONResponse(
                {
                    "status": "ok",
                    "message": "DataDoom API is running. The web UI is not built; "
                    "run `cd frontend && npm install && npm run build`.",
                    "docs": "/api/docs",
                }
            )

        return

    assets = WEBDIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa(full_path: str) -> FileResponse:  # noqa: ANN202
        # Serve real files when they exist; otherwise the SPA entry (client routing).
        candidate = WEBDIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEBDIST / "index.html")
