"""add occurrence tracking to assignments"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202503180001"
down_revision = "202503240003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(
            sa.Column("occurrences_total", sa.Integer(), nullable=True),
        )
        batch_op.add_column(
            sa.Column(
                "occurrences_generated",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # Drop the default now that existing rows have been backfilled
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.alter_column("occurrences_generated", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_column("occurrences_generated")
        batch_op.drop_column("occurrences_total")
