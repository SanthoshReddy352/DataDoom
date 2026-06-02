"""Layered application configuration (03 §7).

Resolution order (lowest precedence first): built-in defaults -> config file
(``<home>/config.toml``) -> environment variables. CLI flags override at the
call site. This module is intentionally tiny and dependency-light so both the
server (``api``/``store``/``jobs``) and the CLI can import it without pulling in
the engine or a web framework.

DataDoom home: ``$DATADOOM_HOME`` or the platform default ``~/.datadoom``.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def datadoom_home() -> Path:
    """Resolve the DataDoom home directory (created on demand by callers)."""
    env = os.environ.get("DATADOOM_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".datadoom"


@dataclass
class Config:
    """Resolved, immutable-ish runtime configuration."""

    home: Path
    db_url: str
    artifacts_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    # `determinism.pinned` mirrors 03 §5; informational here (the engine honors it).
    pinned: bool = False
    telemetry: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def db_path(self) -> Path:
        return self.home / "datadoom.db"

    def ensure_dirs(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


def _load_file(home: Path) -> dict:
    path = home / "config.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def load_config() -> Config:
    """Build a :class:`Config` from defaults, the config file, then the env."""
    home = datadoom_home()
    file_cfg = _load_file(home)

    server = file_cfg.get("server", {})
    storage = file_cfg.get("storage", {})
    determinism = file_cfg.get("determinism", {})
    telemetry = file_cfg.get("telemetry", {})

    artifacts_dir = Path(
        os.environ.get("DATADOOM_ARTIFACTS")
        or storage.get("artifacts_dir")
        or (home / "artifacts")
    ).expanduser()

    db_url = (
        os.environ.get("DATADOOM_DB_URL")
        or storage.get("db_url")
        or f"sqlite:///{(home / 'datadoom.db').as_posix()}"
    )

    host = os.environ.get("DATADOOM_HOST") or server.get("host", "127.0.0.1")
    port = int(os.environ.get("DATADOOM_PORT") or server.get("port", 8000))
    pinned = _as_bool(os.environ.get("DATADOOM_PINNED"), determinism.get("pinned", False))
    tele = _as_bool(os.environ.get("DATADOOM_TELEMETRY"), telemetry.get("enabled", False))

    return Config(
        home=home,
        db_url=db_url,
        artifacts_dir=artifacts_dir,
        host=host,
        port=port,
        pinned=pinned,
        telemetry=tele,
        extra=file_cfg,
    )


def _as_bool(env_value: str | None, default: bool) -> bool:
    if env_value is None:
        return bool(default)
    return env_value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Process-wide cached config. Tests that need isolation call ``load_config``."""
    return load_config()
