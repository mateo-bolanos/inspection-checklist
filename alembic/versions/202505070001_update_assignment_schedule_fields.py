"""Add assignment schedule fields and drop repeat counters"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202505070001"
down_revision = "202505020002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "start_due_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.add_column(sa.Column("end_date", sa.Date(), nullable=True))
        batch_op.drop_column("occurrences_generated")
        batch_op.drop_column("occurrences_total")

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.alter_column("start_due_at", server_default=None)


def downgrade() -> None:
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
        batch_op.drop_column("end_date")
        batch_op.drop_column("start_due_at")

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.alter_column("occurrences_generated", server_default=None)
