"""Add action risk metadata and work order fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202505260001"
down_revision = "202505200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("corrective_actions") as batch_op:
        batch_op.add_column(sa.Column("occurrence_severity", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("injury_severity", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "work_order_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("work_order_number", sa.String(), nullable=True))

    # Drop the default now that existing rows are populated.
    with op.batch_alter_table("corrective_actions") as batch_op:
        batch_op.alter_column("work_order_required", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("corrective_actions") as batch_op:
        batch_op.drop_column("work_order_number")
        batch_op.drop_column("work_order_required")
        batch_op.drop_column("injury_severity")
        batch_op.drop_column("occurrence_severity")
