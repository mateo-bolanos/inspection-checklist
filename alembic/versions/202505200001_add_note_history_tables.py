"""add note history tables"""

from alembic import op
import sqlalchemy as sa


revision = "202505200001"
down_revision = "202505140001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inspection_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inspection_notes_inspection_id", "inspection_notes", ["inspection_id"])

    op.create_table(
        "inspection_response_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "response_id",
            sa.String(),
            sa.ForeignKey("inspection_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inspection_response_notes_response_id", "inspection_response_notes", ["response_id"])

    op.create_table(
        "action_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "action_id",
            sa.Integer(),
            sa.ForeignKey("corrective_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_action_notes_action_id", "action_notes", ["action_id"])


def downgrade() -> None:
    op.drop_index("ix_action_notes_action_id", table_name="action_notes")
    op.drop_table("action_notes")
    op.drop_index("ix_inspection_response_notes_response_id", table_name="inspection_response_notes")
    op.drop_table("inspection_response_notes")
    op.drop_index("ix_inspection_notes_inspection_id", table_name="inspection_notes")
    op.drop_table("inspection_notes")
