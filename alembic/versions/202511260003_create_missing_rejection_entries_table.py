"""Ensure inspection_rejection_entries table exists."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "202511260003_create_missing_rejection_entries_table"
down_revision = "202505260002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "inspection_rejection_entries" in inspector.get_table_names():
        return

    op.create_table(
        "inspection_rejection_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_item_id", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("follow_up_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "inspection_rejection_entries" in inspector.get_table_names():
        op.drop_table("inspection_rejection_entries")
