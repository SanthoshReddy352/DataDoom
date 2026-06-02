"""Database engine/session management (07 §4-5).

SQLite by default with the pragmas doc 07 mandates (WAL, FK on, NORMAL sync).
On startup we run ``alembic upgrade head`` against the on-disk DB so users never
run migrations by hand. For in-memory/test databases (where Alembic's separate
connection cannot see a ``:memory:`` schema) we fall back to ``create_all`` —
the migration is asserted to match the models by a dedicated test.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def utcnow_iso() -> str:
    """Current time as an ISO-8601 UTC string (the on-disk timestamp format)."""
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat()


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_memory(url: str) -> bool:
    return ":memory:" in url or url in {"sqlite://", "sqlite:///:memory:"}


def _install_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


class Database:
    """Owns the SQLAlchemy engine + session factory for one DB URL."""

    def __init__(self, url: str) -> None:
        self.url = url
        connect_args = {"check_same_thread": False} if _is_sqlite(url) else {}
        self.engine: Engine = create_engine(url, future=True, connect_args=connect_args)
        if _is_sqlite(url):
            _install_sqlite_pragmas(self.engine)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False, future=True)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Transactional session scope: commit on success, rollback on error."""
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def create_all(self) -> None:
        """Create the schema directly from the ORM metadata (test/in-memory path)."""
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


def _alembic_config(url: str):  # noqa: ANN202
    from alembic.config import Config

    migrations_dir = Path(__file__).parent / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def init_database(url: str) -> Database:
    """Open the DB and bring its schema up to head (Alembic), creating dirs."""
    if _is_sqlite(url) and not _is_memory(url):
        # Ensure the parent directory for the .db file exists.
        path = url.replace("sqlite:///", "", 1)
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    db = Database(url)
    if _is_memory(url):
        # Alembic uses its own connection; it can't see a private :memory: schema.
        db.create_all()
        return db

    from alembic import command

    command.upgrade(_alembic_config(url), "head")
    return db
