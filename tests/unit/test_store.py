"""Store layer: CRUD, spec immutability, cascade delete, migration↔models parity.

Covers 17 step 7's test bullets — "CRUD; spec immutability (edit → new version);
cascade delete" — plus a guard that the Alembic ``0001_init`` migration produces
the same tables the ORM declares.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from datadoom.store import (
    ArtifactRepository,
    Base,
    Database,
    DatasetRepository,
    ReportRepository,
    RunRepository,
    SpecRepository,
    init_database,
)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return init_database(f"sqlite:///{(tmp_path / 'datadoom.db').as_posix()}")


def _body(rows: int = 10) -> dict:
    return {
        "datadoom_version": "1",
        "name": "demo",
        "rows": rows,
        "features": {"age": {"type": "numeric", "dist": "normal", "params": {"mean": 1, "std": 1}}},
    }


def test_alembic_migration_matches_models(db: Database) -> None:
    from sqlalchemy import inspect

    tables = set(inspect(db.engine).get_table_names())
    expected = set(Base.metadata.tables.keys())
    # alembic_version is Alembic's bookkeeping table; ignore it.
    assert expected <= tables
    assert "alembic_version" in tables


def test_dataset_crud(db: Database) -> None:
    with db.session() as s:
        repo = DatasetRepository(s)
        d = repo.create("alpha", "first")
        did = d.dataset_id
    with db.session() as s:
        repo = DatasetRepository(s)
        got = repo.get(did)
        assert got is not None and got.name == "alpha" and got.status == "draft"
        repo.update(got, name="alpha2")
    with db.session() as s:
        assert DatasetRepository(s).get(did).name == "alpha2"


def test_spec_immutability_creates_new_version(db: Database) -> None:
    with db.session() as s:
        d = DatasetRepository(s).create("imm")
        specs = SpecRepository(s)
        v1 = specs.create_version(d, _body(10), "h1", "1")
        v2 = specs.create_version(d, _body(20), "h2", "1")
        # New version, distinct row, current repointed; v1 untouched.
        assert (v1.version, v2.version) == (1, 2)
        assert v1.spec_id != v2.spec_id
        assert d.current_spec_id == v2.spec_id
        assert v1.body["rows"] == 10  # original snapshot is immutable
        assert len(specs.history(d.dataset_id)) == 2


def test_cascade_delete_removes_children(db: Database) -> None:
    with db.session() as s:
        d = DatasetRepository(s).create("casc")
        spec = SpecRepository(s).create_version(d, _body(), "h", "1")
        run = RunRepository(s).create(d.dataset_id, spec.spec_id, 1)
        ArtifactRepository(s).add(run.run_id, "clean", "csv", "file:x", "c" * 64, 10, "full")
        ReportRepository(s).upsert(run.run_id, {"compliance_score": 1.0})
        did, rid = d.dataset_id, run.run_id

    with db.session() as s:
        DatasetRepository(s).delete(DatasetRepository(s).get(did))

    with db.session() as s:
        assert DatasetRepository(s).get(did) is None
        assert RunRepository(s).get(rid) is None
        assert ArtifactRepository(s).list_for_run(rid) == []
        assert ReportRepository(s).get_for_run(rid) is None


def test_get_by_name_lookup(db: Database) -> None:
    # In local mode owner_id is NULL, so SQLite's unique index treats names as
    # distinct (NULLs differ); duplicate-name protection is enforced at the API
    # layer (409). The repository's name lookup is what that check relies on.
    with db.session() as s:
        DatasetRepository(s).create("findme", "x")
    with db.session() as s:
        found = DatasetRepository(s).get_by_name("findme")
        assert found is not None and found.description == "x"
        assert DatasetRepository(s).get_by_name("absent") is None
