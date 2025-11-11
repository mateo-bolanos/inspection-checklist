"""rebuild corrective actions to support lifecycle tracking"""
from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime
from typing import Optional

from alembic import op
from sqlalchemy.orm import Session

revision = "202502120001"
down_revision = "202502080001"
branch_labels = None
depends_on = None


def _maybe_parse_datetime(value: object) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value  # type: ignore[return-value]
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _coerce_int(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_actions_backup = inspector.has_table("corrective_actions_old")
    has_media_backup = inspector.has_table("media_files_old")
    has_new_actions = inspector.has_table("corrective_actions")
    has_new_media = inspector.has_table("media_files")

    needs_rebuild = True
    if has_actions_backup and has_new_actions:
        columns = {column["name"] for column in inspector.get_columns("corrective_actions")}
        if "started_by_id" in columns:
            with Session(bind=bind) as check_session:
                old_actions_count = (
                    check_session.execute(sa.text("SELECT COUNT(*) FROM corrective_actions_old")).scalar() or 0
                )
                new_actions_count = (
                    check_session.execute(sa.text("SELECT COUNT(*) FROM corrective_actions")).scalar() or 0
                )
                if has_media_backup and has_new_media:
                    old_media_count = (
                        check_session.execute(sa.text("SELECT COUNT(*) FROM media_files_old")).scalar() or 0
                    )
                    new_media_count = (
                        check_session.execute(sa.text("SELECT COUNT(*) FROM media_files")).scalar() or 0
                    )
                else:
                    old_media_count = 0
                    new_media_count = 0
                if new_actions_count == old_actions_count and new_media_count == old_media_count:
                    needs_rebuild = False

    if not needs_rebuild:
        if has_media_backup:
            op.drop_table("media_files_old")
        if has_actions_backup:
            op.drop_table("corrective_actions_old")
        return

    if has_actions_backup:
        if has_new_actions:
            op.drop_table("corrective_actions")
    else:
        op.rename_table("corrective_actions", "corrective_actions_old")
        has_actions_backup = True

    if has_media_backup:
        if has_new_media:
            op.drop_table("media_files")
    else:
        op.rename_table("media_files", "media_files_old")
        has_media_backup = True

    op.create_table(
        "corrective_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
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
        sa.Column("started_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("closed_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "media_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "response_id",
            sa.String(),
            sa.ForeignKey("inspection_responses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "action_id",
            sa.Integer(),
            sa.ForeignKey("corrective_actions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("file_url", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    session = Session(bind=bind)
    metadata = sa.MetaData()

    try:
        new_actions = sa.Table("corrective_actions", metadata, autoload_with=bind)
        new_media = sa.Table("media_files", metadata, autoload_with=bind)

        id_map: dict[int, int] = {}
        if has_actions_backup:
            actions_query = sa.text(
                """
                SELECT
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
                FROM corrective_actions_old
                ORDER BY created_at, id
                """
            )
            for row in session.execute(actions_query).mappings():
                legacy_id = _coerce_int(row["id"])
                status = row["status"]
                closed_at = _maybe_parse_datetime(row["closed_at"])
                created_at = _maybe_parse_datetime(row["created_at"])
                due_date = _maybe_parse_datetime(row["due_date"])
                result = session.execute(
                    sa.insert(new_actions).values(
                        inspection_id=row["inspection_id"],
                        response_id=row["response_id"],
                        title=row["title"],
                        description=row["description"],
                        severity=row["severity"],
                        due_date=due_date,
                        assigned_to_id=row["assigned_to_id"],
                        status=status,
                        started_by_id=row["created_by_id"],
                        closed_by_id=row["created_by_id"] if status == "closed" and closed_at is not None else None,
                        created_at=created_at,
                        closed_at=closed_at,
                        resolution_notes=None,
                    )
                )
                if legacy_id is not None:
                    id_map[legacy_id] = result.inserted_primary_key[0]

        if has_media_backup:
            session.flush()
            media_query = sa.text(
                """
                SELECT
                    id,
                    response_id,
                    action_id,
                    file_url,
                    description,
                    uploaded_by_id,
                    created_at
                FROM media_files_old
                """
            )
            for media_row in session.execute(media_query).mappings():
                legacy_action_id = _coerce_int(media_row["action_id"])
                created_at = _maybe_parse_datetime(media_row["created_at"])
                session.execute(
                    sa.insert(new_media).values(
                        id=media_row["id"],
                        response_id=media_row["response_id"],
                        action_id=id_map.get(legacy_action_id),
                        file_url=media_row["file_url"],
                        description=media_row["description"],
                        uploaded_by_id=media_row["uploaded_by_id"],
                        created_at=created_at,
                    )
                )

        session.commit()
    finally:
        session.close()

    if has_media_backup:
        op.drop_table("media_files_old")
    if has_actions_backup:
        op.drop_table("corrective_actions_old")


def downgrade() -> None:
    raise RuntimeError("Downgrade not supported for corrective action rebuild")
