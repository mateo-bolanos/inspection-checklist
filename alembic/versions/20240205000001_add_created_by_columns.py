"""add created_by tracking for inspections and actions

Revision ID: 20240205000001
Revises: 20240101000000
Create Date: 2024-02-05 00:00:01.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20240205000001"
down_revision = "20240101000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("inspections", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_by_id",
                sa.String(),
                sa.ForeignKey("users.id", name="fk_inspections_created_by_id_users"),
                nullable=True,
            )
        )

    with op.batch_alter_table("corrective_actions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_by_id",
                sa.String(),
                sa.ForeignKey("users.id", name="fk_corrective_actions_created_by_id_users"),
                nullable=True,
            )
        )

    op.execute("UPDATE inspections SET created_by_id = inspector_id WHERE created_by_id IS NULL")
    op.execute(
        """
        UPDATE corrective_actions
        SET created_by_id = (
            SELECT inspector_id FROM inspections WHERE inspections.id = corrective_actions.inspection_id
        )
        WHERE created_by_id IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("corrective_actions", schema=None) as batch_op:
        batch_op.drop_column("created_by_id")

    with op.batch_alter_table("inspections", schema=None) as batch_op:
        batch_op.drop_column("created_by_id")
