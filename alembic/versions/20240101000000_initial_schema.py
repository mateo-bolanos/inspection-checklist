"""initial schema

Revision ID: 20240101000000
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20240101000000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=False, server_default=""),
        sa.Column("role", sa.String(), nullable=False, server_default="inspector"),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "checklist_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "template_sections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "template_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("section_id", sa.String(), sa.ForeignKey("template_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "inspections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("checklist_templates.id"), nullable=False),
        sa.Column("inspector_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "inspection_responses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("inspection_id", sa.String(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_item_id", sa.String(), sa.ForeignKey("template_items.id"), nullable=False),
        sa.Column("result", sa.String(), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
    )

    op.create_table(
        "corrective_actions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("inspection_id", sa.String(), sa.ForeignKey("inspections.id"), nullable=False),
        sa.Column("response_id", sa.String(), sa.ForeignKey("inspection_responses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("assigned_to_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "media_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("response_id", sa.String(), sa.ForeignKey("inspection_responses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("action_id", sa.String(), sa.ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("file_url", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("media_files")
    op.drop_table("corrective_actions")
    op.drop_table("inspection_responses")
    op.drop_table("inspections")
    op.drop_table("template_items")
    op.drop_table("template_sections")
    op.drop_table("checklist_templates")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
