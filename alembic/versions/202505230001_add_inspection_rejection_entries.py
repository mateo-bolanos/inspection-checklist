"""Add inspection rejection entries table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202505230001_add_inspection_rejection_entries"
down_revision = "202505260001"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.drop_table("inspection_rejection_entries")
