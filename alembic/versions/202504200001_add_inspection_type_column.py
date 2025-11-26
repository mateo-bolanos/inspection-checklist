"""Add inspection_type column to inspections."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202504200001"
down_revision = "202504010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inspections", sa.Column("inspection_type", sa.String(), nullable=True))

    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT inspections.id, checklist_templates.name AS template_name
            FROM inspections
            LEFT JOIN checklist_templates ON checklist_templates.id = inspections.template_id
            """
        )
    )
    rows = result.fetchall()
    for row in rows:
        fallback = (row.template_name or "").strip() or "Inspection"
        conn.execute(
            sa.text("UPDATE inspections SET inspection_type = :inspection_type WHERE id = :inspection_id"),
            {"inspection_type": fallback, "inspection_id": row.id},
        )


def downgrade() -> None:
    op.drop_column("inspections", "inspection_type")
