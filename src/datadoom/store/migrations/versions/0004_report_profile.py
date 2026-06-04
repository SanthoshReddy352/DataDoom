"""0004 — add ``reports.profile`` (per-column data profile / "Column Guide").

Adds the JSON column ``ReportRepository.upsert`` writes the per-column profile
into: summary statistics, role, causal parents, failure attribution, and
ML-handling advice per column. Separate from earlier revisions so databases
created before this column existed upgrade in place on startup.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_report_profile"
down_revision = "0003_run_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "profile")
