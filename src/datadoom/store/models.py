"""SQLAlchemy ORM models — mirror docs 06 §3 and 07 §2.

Portable DDL (SQLite default, Postgres-compatible): UUID string PKs, ISO-8601 UTC
timestamps stored as TEXT, JSON columns via SQLAlchemy's generic ``JSON`` type
(SQLite ``JSON1`` / Postgres ``JSONB``).

Circular references (``datasets.current_spec_id`` ⇄ ``specs.dataset_id`` and
``datasets.latest_run_id``) are kept as plain indexed columns — "soft" FKs the
application maintains — exactly as doc 07 notes, to avoid SQLite's
create-order / ALTER-FK limitations. The hard, cascade-enforced FKs all point
"downward" (spec → dataset, run → dataset/spec, artifact/report → run).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON as SAJSON
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DatasetRow(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # Soft references (app-maintained; see module docstring).
    current_spec_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    # passive_deletes lets the DB's ON DELETE CASCADE do the work in one statement,
    # avoiding ORM delete-ordering issues across the specs⇄runs FK.
    specs: Mapped[list[SpecRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    runs: Mapped[list[GenerationRunRow]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ux_datasets_owner_name", "owner_id", "name", unique=True),
        Index("ix_datasets_status", "status"),
    )


class SpecRow(Base):
    __tablename__ = "specs"

    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False
    )
    spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(SAJSON, nullable=False)
    datadoom_version: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    dataset: Mapped[DatasetRow] = relationship(back_populates="specs")

    __table_args__ = (
        Index("ix_specs_dataset", "dataset_id"),
        Index("ix_specs_hash", "spec_hash"),
        Index("ux_specs_dataset_version", "dataset_id", "version", unique=True),
    )


class GenerationRunRow(Base):
    __tablename__ = "generation_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False
    )
    spec_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("specs.spec_id", ondelete="CASCADE"), nullable=False
    )
    # Human label for the generation. Optional for rows created before naming
    # existed; the UI mandates one on new runs (falls back to the id for display).
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    dataset: Mapped[DatasetRow] = relationship(back_populates="runs")
    # Read-only handle to the immutable spec snapshot this run was generated from,
    # so callers can surface its ``spec_hash`` (the version-control anchor).
    spec: Mapped[SpecRow] = relationship(viewonly=True)
    artifacts: Mapped[list[ArtifactRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    report: Mapped[ReportRow | None] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False, passive_deletes=True
    )

    __table_args__ = (
        Index("ix_runs_dataset", "dataset_id"),
        Index("ix_runs_status", "status"),
        Index("ix_runs_repro", "spec_id", "seed"),
    )


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_runs.run_id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String, nullable=False)  # clean | injected
    split: Mapped[str | None] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    run: Mapped[GenerationRunRow] = relationship(back_populates="artifacts")

    __table_args__ = (Index("ix_artifacts_run", "run_id"),)


class ReportRow(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    compliance_score: Mapped[float | None] = mapped_column(nullable=True)
    distribution: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    correlation: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    mutual_information: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    causal_truth: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    difficulty: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    failures: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    profile: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    determinism: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    run: Mapped[GenerationRunRow] = relationship(back_populates="report")


class PluginRow(Base):
    __tablename__ = "plugins"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    schema: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
