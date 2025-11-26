"""Add template reference to assignments."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202504010001"
down_revision = "202503180001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("template_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assignments_template_id",
            "checklist_templates",
            ["template_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_constraint("fk_assignments_template_id", type_="foreignkey")
        batch_op.drop_column("template_id")
