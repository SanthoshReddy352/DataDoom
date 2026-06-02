"""0002 — add ``reports.mutual_information`` (P2 causal: MI matrix, 05 §7).

Adds the JSON column that ``ReportRepository.upsert`` writes the mutual-information
matrix into. Separate from ``0001_init`` so databases created before this column
existed are upgraded in place on startup (``alembic upgrade head``).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_report_mutual_information"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("mutual_information", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "mutual_information")
