"""0001 init — core tables (07 §2, no team-mode ``users``).

Revision ID: 0001_init
Revises:
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        # Soft references (app-maintained) to break the datasets⇄specs cycle.
        sa.Column("current_spec_id", sa.String(length=36), nullable=True),
        sa.Column("latest_run_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ux_datasets_owner_name", "datasets", ["owner_id", "name"], unique=True)
    op.create_index("ix_datasets_status", "datasets", ["status"])

    op.create_table(
        "specs",
        sa.Column("spec_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=36),
            sa.ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("spec_hash", sa.String(length=64), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("datadoom_version", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_specs_dataset", "specs", ["dataset_id"])
    op.create_index("ix_specs_hash", "specs", ["spec_hash"])
    op.create_index(
        "ux_specs_dataset_version", "specs", ["dataset_id", "version"], unique=True
    )

    op.create_table(
        "generation_runs",
        sa.Column("run_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=36),
            sa.ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "spec_id",
            sa.String(length=36),
            sa.ForeignKey("specs.spec_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(), nullable=True),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.String(), nullable=True),
        sa.Column("finished_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_runs_dataset", "generation_runs", ["dataset_id"])
    op.create_index("ix_runs_status", "generation_runs", ["status"])
    op.create_index("ix_runs_repro", "generation_runs", ["spec_id", "seed"])

    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("generation_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("split", sa.String(), nullable=True),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("storage_uri", sa.String(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_artifacts_run", "artifacts", ["run_id"])

    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("generation_runs.run_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("distribution", sa.JSON(), nullable=True),
        sa.Column("correlation", sa.JSON(), nullable=True),
        sa.Column("causal_truth", sa.JSON(), nullable=True),
        sa.Column("difficulty", sa.JSON(), nullable=True),
        sa.Column("failures", sa.JSON(), nullable=True),
        sa.Column("determinism", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )

    op.create_table(
        "plugins",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("schema", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("plugins")
    op.drop_table("reports")
    op.drop_index("ix_artifacts_run", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_runs_repro", table_name="generation_runs")
    op.drop_index("ix_runs_status", table_name="generation_runs")
    op.drop_index("ix_runs_dataset", table_name="generation_runs")
    op.drop_table("generation_runs")
    op.drop_index("ux_specs_dataset_version", table_name="specs")
    op.drop_index("ix_specs_hash", table_name="specs")
    op.drop_index("ix_specs_dataset", table_name="specs")
    op.drop_table("specs")
    op.drop_index("ix_datasets_status", table_name="datasets")
    op.drop_index("ux_datasets_owner_name", table_name="datasets")
    op.drop_table("datasets")
