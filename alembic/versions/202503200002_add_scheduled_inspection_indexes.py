"""add indexes for scheduled inspection dashboard queries"""
from __future__ import annotations

from alembic import op

revision = "202503200002"
down_revision = "202503070001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_scheduled_inspections_period_start",
        "scheduled_inspections",
        ["period_start"],
    )
    op.create_index(
        "ix_scheduled_inspections_status",
        "scheduled_inspections",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_inspections_status", table_name="scheduled_inspections")
    op.drop_index("ix_scheduled_inspections_period_start", table_name="scheduled_inspections")
