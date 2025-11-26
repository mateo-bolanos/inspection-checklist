"""Drop critical severity and update SLA defaults"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202505140001"
down_revision = "202505070001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind is None:
        return

    with op.batch_alter_table("severity_sla") as batch_op:
        batch_op.drop_column("critical_days")

    severity_sla = sa.table(
        "severity_sla",
        sa.column("low_days", sa.Integer()),
        sa.column("medium_days", sa.Integer()),
        sa.column("high_days", sa.Integer()),
    )
    bind.execute(
        sa.update(severity_sla).values(
            low_days=30,
            medium_days=7,
            high_days=1,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind is None:
        return

    with op.batch_alter_table("severity_sla") as batch_op:
        batch_op.add_column(
            sa.Column(
                "critical_days",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )

    severity_sla = sa.table(
        "severity_sla",
        sa.column("low_days", sa.Integer()),
        sa.column("medium_days", sa.Integer()),
        sa.column("high_days", sa.Integer()),
        sa.column("critical_days", sa.Integer()),
    )
    bind.execute(
        sa.update(severity_sla).values(
            low_days=30,
            medium_days=14,
            high_days=7,
            critical_days=1,
        )
    )

    with op.batch_alter_table("severity_sla") as batch_op:
        batch_op.alter_column("critical_days", server_default=None)
