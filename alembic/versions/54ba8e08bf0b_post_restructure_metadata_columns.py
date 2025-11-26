"""restore evidence and metadata columns after corrective-action rebuild"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "54ba8e08bf0b"
down_revision = "202502120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("template_items") as batch_op:
        batch_op.add_column(
            sa.Column("requires_attachment_on_fail", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.alter_column("requires_attachment_on_fail", server_default=None)

    with op.batch_alter_table("inspections") as batch_op:
        batch_op.add_column(sa.Column("location_id", sa.String(), nullable=True))

    with op.batch_alter_table("corrective_actions") as batch_op:
        batch_op.add_column(sa.Column("due_date_note", sa.Text(), nullable=True))

    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(sa.Column("mime_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_column("file_size")
        batch_op.drop_column("mime_type")

    with op.batch_alter_table("corrective_actions") as batch_op:
        batch_op.drop_column("due_date_note")

    with op.batch_alter_table("inspections") as batch_op:
        batch_op.drop_column("location_id")

    with op.batch_alter_table("template_items") as batch_op:
        batch_op.drop_column("requires_attachment_on_fail")
