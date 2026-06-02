"""0003 — add ``generation_runs.name`` (named generations).

Each generation gets an optional human label. Nullable so databases created
before naming existed upgrade in place; the UI requires a name on new runs and
falls back to the run id for older, unnamed rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_run_name"
down_revision = "0002_report_mutual_information"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_runs", sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_runs", "name")
