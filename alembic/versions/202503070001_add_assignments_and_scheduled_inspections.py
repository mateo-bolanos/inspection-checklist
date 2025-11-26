"""introduce assignments and scheduled inspections"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202503070001"
down_revision = "54ba8e08bf0b"
branch_labels = None
depends_on = None
FK_INSPECTION_SCHEDULE = "fk_inspections_scheduled_inspection"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("assignments"):
        op.create_table(
            "assignments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("inspection_type", sa.String(), nullable=False),
            sa.Column("assigned_to_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("frequency", sa.String(), nullable=False, server_default="weekly"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if not inspector.has_table("scheduled_inspections"):
        op.create_table(
            "scheduled_inspections",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "assignment_id",
                sa.Integer(),
                sa.ForeignKey("assignments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("assignment_id", "period_start", name="uq_scheduled_assignment_period"),
        )

    inspection_columns = {column["name"] for column in inspector.get_columns("inspections")}
    if "scheduled_inspection_id" not in inspection_columns:
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "scheduled_inspection_id",
                    sa.Integer(),
                    nullable=True,
                )
            )
            batch_op.create_foreign_key(
                FK_INSPECTION_SCHEDULE,
                "scheduled_inspections",
                ["scheduled_inspection_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(
            "ix_inspections_scheduled_inspection_id", "inspections", ["scheduled_inspection_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    inspection_columns = {column["name"] for column in inspector.get_columns("inspections")}
    if "scheduled_inspection_id" in inspection_columns:
        op.drop_index("ix_inspections_scheduled_inspection_id", table_name="inspections")
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.drop_constraint(FK_INSPECTION_SCHEDULE, type_="foreignkey")
            batch_op.drop_column("scheduled_inspection_id")

    if inspector.has_table("scheduled_inspections"):
        op.drop_table("scheduled_inspections")

    if inspector.has_table("assignments"):
        op.drop_table("assignments")
