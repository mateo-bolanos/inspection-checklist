"""Add severity SLA table and harden media files"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503240003"
down_revision = ("202503150001", "202503200002")
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind is None:
        return
    op.create_table(
        "severity_sla",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("low_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("medium_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("high_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("critical_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    inspector = sa.inspect(bind)
    media_columns = {column["name"] for column in inspector.get_columns("media_files")}

    with op.batch_alter_table("media_files") as batch_op:
        if "storage_path" not in media_columns:
            batch_op.add_column(sa.Column("storage_path", sa.String(), nullable=True))
        if "original_name" not in media_columns:
            batch_op.add_column(sa.Column("original_name", sa.String(), nullable=True))
        if "file_size" in media_columns:
            batch_op.alter_column("file_size", new_column_name="size_bytes")
        elif "size_bytes" not in media_columns:
            batch_op.add_column(sa.Column("size_bytes", sa.Integer(), nullable=True))

    media = sa.table(
        "media_files",
        sa.column("id", sa.String()),
        sa.column("file_url", sa.String()),
        sa.column("storage_path", sa.String()),
    )
    results = bind.execute(sa.select(media.c.id, media.c.file_url)).fetchall()
    for media_id, file_url in results:
        filename = ""
        if file_url:
            filename = file_url.rsplit("/", 1)[-1]
        if not filename:
            filename = f"{media_id}"
        bind.execute(
            sa.update(media)
            .where(media.c.id == media_id)
            .values(
                storage_path=filename,
                file_url=f"/files/{media_id}/download",
            )
        )

    # SQLite struggles with ALTER COLUMN in migrations; rely on application-level validation.


def downgrade() -> None:
    bind = op.get_bind()
    if bind is None:
        return
    media = sa.table(
        "media_files",
        sa.column("id", sa.String()),
        sa.column("file_url", sa.String()),
        sa.column("storage_path", sa.String()),
    )
    results = bind.execute(sa.select(media.c.id, media.c.storage_path)).fetchall()
    for media_id, storage_path in results:
        legacy_url = f"/uploads/{storage_path}" if storage_path else f"/uploads/{media_id}"
        bind.execute(
            sa.update(media)
            .where(media.c.id == media_id)
            .values(file_url=legacy_url)
        )

    inspector = sa.inspect(bind)
    media_columns = {column["name"] for column in inspector.get_columns("media_files")}

    with op.batch_alter_table("media_files") as batch_op:
        if "size_bytes" in media_columns and "file_size" not in media_columns:
            batch_op.alter_column("size_bytes", new_column_name="file_size")
        elif "size_bytes" in media_columns:
            batch_op.drop_column("size_bytes")
        if "original_name" in media_columns:
            batch_op.drop_column("original_name")
        if "storage_path" in media_columns:
            batch_op.drop_column("storage_path")

    op.drop_table("severity_sla")
