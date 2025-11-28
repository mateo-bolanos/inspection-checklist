"""Add rejection reason tracking and follow-up assignment metadata."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202505260002"
down_revision = "202505230001_add_inspection_rejection_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    inspection_columns = {col["name"] for col in inspector.get_columns("inspections")}
    if "rejection_reason" not in inspection_columns:
        op.add_column("inspections", sa.Column("rejection_reason", sa.Text(), nullable=True))
    if "rejected_by_id" not in inspection_columns:
        op.add_column("inspections", sa.Column("rejected_by_id", sa.String(), nullable=True))

    assignment_columns = {col["name"] for col in inspector.get_columns("assignments")}
    if "priority" not in assignment_columns:
        op.add_column("assignments", sa.Column("priority", sa.String(), nullable=False, server_default="normal"))
    if "tag" not in assignment_columns:
        op.add_column("assignments", sa.Column("tag", sa.String(), nullable=True))
    if "notes" not in assignment_columns:
        op.add_column("assignments", sa.Column("notes", sa.Text(), nullable=True))
    if "source_inspection_id" not in assignment_columns:
        op.add_column(
            "assignments",
            sa.Column(
                "source_inspection_id",
                sa.Integer(),
                sa.ForeignKey("inspections.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    if "priority" not in assignment_columns:
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.alter_column("priority", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_column("source_inspection_id")
        batch_op.drop_column("notes")
        batch_op.drop_column("tag")
        batch_op.drop_column("priority")

    with op.batch_alter_table("inspections") as batch_op:
        batch_op.drop_column("rejected_by_id")
        batch_op.drop_column("rejection_reason")
