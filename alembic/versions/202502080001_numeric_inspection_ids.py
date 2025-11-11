"""switch inspections to numeric ids

Revision ID: 202502080001
Revises: 20240205000001
Create Date: 2025-02-08 00:00:01.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "202502080001"
down_revision = "20240205000001"
branch_labels = None
depends_on = None


INSPECTION_COLUMNS = [
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("template_id", sa.String(), sa.ForeignKey("checklist_templates.id"), nullable=False),
    sa.Column("inspector_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("created_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("status", sa.String(), nullable=False, server_default="draft"),
    sa.Column("location", sa.String(), nullable=True),
    sa.Column("notes", sa.Text(), nullable=True),
    sa.Column("overall_score", sa.Float(), nullable=True),
    sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column("submitted_at", sa.DateTime(), nullable=True),
    sa.Column("approved_at", sa.DateTime(), nullable=True),
    sa.Column("rejected_at", sa.DateTime(), nullable=True),
]


INSPECTION_RESPONSE_COLUMNS = [
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
    sa.Column(
        "template_item_id",
        sa.String(),
        sa.ForeignKey("template_items.id"),
        nullable=False,
    ),
    sa.Column("result", sa.String(), nullable=False, server_default="pending"),
    sa.Column("note", sa.Text(), nullable=True),
]


CORRECTIVE_ACTION_COLUMNS = [
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id"), nullable=False),
    sa.Column(
        "response_id",
        sa.String(),
        sa.ForeignKey("inspection_responses.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("title", sa.String(), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("severity", sa.String(), nullable=False, server_default="medium"),
    sa.Column("due_date", sa.DateTime(), nullable=True),
    sa.Column("assigned_to_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
    sa.Column("status", sa.String(), nullable=False, server_default="open"),
    sa.Column("created_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column("closed_at", sa.DateTime(), nullable=True),
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))

    op.rename_table("corrective_actions", "corrective_actions_old")
    op.rename_table("inspection_responses", "inspection_responses_old")
    op.rename_table("inspections", "inspections_old")

    op.create_table("inspections", *INSPECTION_COLUMNS, sqlite_autoincrement=True)

    op.create_table(
        "inspection_transfer",
        sa.Column("old_id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("inspector_id", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("new_id", sa.Integer(), nullable=False, unique=True),
    )

    op.execute(
        """
        INSERT INTO inspection_transfer (
            old_id,
            template_id,
            inspector_id,
            created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at,
            new_id
        )
        SELECT
            id AS old_id,
            template_id,
            inspector_id,
            COALESCE(created_by_id, inspector_id) AS created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at,
            ROW_NUMBER() OVER (ORDER BY started_at, id)
        FROM inspections_old
        """
    )

    op.execute(
        """
        INSERT INTO inspections (
            id,
            template_id,
            inspector_id,
            created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at
        )
        SELECT
            new_id,
            template_id,
            inspector_id,
            created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at
        FROM inspection_transfer
        """
    )

    op.create_table(
        "inspection_id_map",
        sa.Column("old_id", sa.String(), primary_key=True),
        sa.Column("new_id", sa.Integer(), nullable=False, unique=True),
    )

    op.execute(
        """
        INSERT INTO inspection_id_map (old_id, new_id)
        SELECT old_id, new_id
        FROM inspection_transfer
        """
    )

    op.drop_table("inspection_transfer")

    op.create_table("inspection_responses", *INSPECTION_RESPONSE_COLUMNS)

    op.execute(
        """
        INSERT INTO inspection_responses (
            id,
            inspection_id,
            template_item_id,
            result,
            note
        )
        SELECT
            ir.id,
            map.new_id,
            ir.template_item_id,
            ir.result,
            ir.note
        FROM inspection_responses_old ir
        JOIN inspection_id_map map ON map.old_id = ir.inspection_id
        """
    )

    op.create_table("corrective_actions", *CORRECTIVE_ACTION_COLUMNS)

    op.execute(
        """
        INSERT INTO corrective_actions (
            id,
            inspection_id,
            response_id,
            title,
            description,
            severity,
            due_date,
            assigned_to_id,
            status,
            created_by_id,
            created_at,
            closed_at
        )
        SELECT
            ca.id,
            map.new_id,
            ca.response_id,
            ca.title,
            ca.description,
            ca.severity,
            ca.due_date,
            ca.assigned_to_id,
            ca.status,
            COALESCE(ca.created_by_id, insp.created_by_id),
            ca.created_at,
            ca.closed_at
        FROM corrective_actions_old ca
        JOIN inspection_id_map map ON map.old_id = ca.inspection_id
        LEFT JOIN inspections insp ON insp.id = map.new_id
        """
    )

    op.drop_table("inspection_id_map")

    op.drop_table("corrective_actions_old")
    op.drop_table("inspection_responses_old")
    op.drop_table("inspections_old")

    try:
        bind.execute(
            sa.text(
                "UPDATE sqlite_sequence SET seq = (SELECT COALESCE(MAX(id), 0) FROM inspections) WHERE name = 'inspections'"
            )
        )
    except sa.exc.DBAPIError:
        pass

    bind.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))

    op.rename_table("corrective_actions", "corrective_actions_new")
    op.rename_table("inspection_responses", "inspection_responses_new")
    op.rename_table("inspections", "inspections_new")

    op.create_table(
        "inspections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("checklist_templates.id"), nullable=False),
        sa.Column("inspector_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
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
        "inspection_id_map",
        sa.Column("new_id", sa.Integer(), primary_key=True),
        sa.Column("old_id", sa.String(), nullable=False, unique=True),
    )

    op.execute(
        """
        INSERT INTO inspections (
            id,
            template_id,
            inspector_id,
            created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at
        )
        SELECT
            CAST(id AS TEXT) AS id,
            template_id,
            inspector_id,
            created_by_id,
            status,
            location,
            notes,
            overall_score,
            started_at,
            submitted_at,
            approved_at,
            rejected_at
        FROM inspections_new
        """
    )

    op.execute(
        """
        INSERT INTO inspection_id_map (new_id, old_id)
        SELECT id, CAST(id AS TEXT)
        FROM inspections_new
        """
    )

    op.create_table(
        "inspection_responses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("inspection_id", sa.String(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "template_item_id",
            sa.String(),
            sa.ForeignKey("template_items.id"),
            nullable=False,
        ),
        sa.Column("result", sa.String(), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
    )

    op.execute(
        """
        INSERT INTO inspection_responses (
            id,
            inspection_id,
            template_item_id,
            result,
            note
        )
        SELECT
            ir.id,
            map.old_id,
            ir.template_item_id,
            ir.result,
            ir.note
        FROM inspection_responses_new ir
        JOIN inspection_id_map map ON map.new_id = ir.inspection_id
        """
    )

    op.create_table(
        "corrective_actions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("inspection_id", sa.String(), sa.ForeignKey("inspections.id"), nullable=False),
        sa.Column(
            "response_id",
            sa.String(),
            sa.ForeignKey("inspection_responses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("assigned_to_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )

    op.execute(
        """
        INSERT INTO corrective_actions (
            id,
            inspection_id,
            response_id,
            title,
            description,
            severity,
            due_date,
            assigned_to_id,
            status,
            created_by_id,
            created_at,
            closed_at
        )
        SELECT
            ca.id,
            map.old_id,
            ca.response_id,
            ca.title,
            ca.description,
            ca.severity,
            ca.due_date,
            ca.assigned_to_id,
            ca.status,
            ca.created_by_id,
            ca.created_at,
            ca.closed_at
        FROM corrective_actions_new ca
        JOIN inspection_id_map map ON map.new_id = ca.inspection_id
        """
    )

    op.drop_table("inspection_id_map")

    op.drop_table("corrective_actions_new")
    op.drop_table("inspection_responses_new")
    op.drop_table("inspections_new")

    bind.execute(sa.text("PRAGMA foreign_keys=ON"))
