"""Drop inspection_type column from inspections"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202505020001"
down_revision = "202505010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("inspections")}
    if "inspection_type" in column_names:
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.drop_column("inspection_type")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("inspections")}
    if "inspection_type" not in column_names:
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.add_column(
                sa.Column("inspection_type", sa.String(), nullable=True),
            )
