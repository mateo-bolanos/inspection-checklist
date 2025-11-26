"""Add inspection origin column"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202505010001"
down_revision = "202504200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("inspections")}
    if "inspection_origin" not in column_names:
        op.add_column(
            "inspections",
            sa.Column("inspection_origin", sa.String(), nullable=False, server_default="independent"),
        )
    op.execute(
        "UPDATE inspections SET inspection_origin = 'assignment' WHERE scheduled_inspection_id IS NOT NULL"
    )
    op.execute(
        "UPDATE inspections SET inspection_origin = 'independent' WHERE inspection_origin IS NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("inspections")}
    if "inspection_origin" in column_names:
        op.drop_column("inspections", "inspection_origin")
