from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    CorrectiveAction,
    Inspection,
    InspectionResponse,
    MediaFile,
    User,
    UserRole,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_media_file(
    db: Session,
    *,
    content: bytes,
    original_name: str | None,
    response_id: str | None,
    action_id: int | None,
    uploaded_by: str | None,
) -> MediaFile:
    suffix = Path(original_name or "upload").suffix
    filename = f"{uuid.uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)
    file_url = f"/uploads/{filename}"
    media = MediaFile(
        response_id=response_id,
        action_id=action_id,
        file_url=file_url,
        uploaded_by_id=uploaded_by,
        description=f"Uploaded {original_name}" if original_name else None,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def list_media_files(
    db: Session,
    user: User,
    *,
    action_id: int | None = None,
    response_id: str | None = None,
) -> list[MediaFile]:
    query = db.query(MediaFile).options(
        selectinload(MediaFile.response).selectinload(InspectionResponse.inspection),
        selectinload(MediaFile.action).selectinload(CorrectiveAction.inspection),
        selectinload(MediaFile.uploaded_by),
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.filter(
            or_(
                MediaFile.uploaded_by_id == user.id,
                MediaFile.response.has(
                    InspectionResponse.inspection.has(Inspection.inspector_id == user.id),
                ),
                MediaFile.action.has(
                    CorrectiveAction.inspection.has(Inspection.inspector_id == user.id),
                ),
            )
        )
    if action_id is not None:
        query = query.filter(MediaFile.action_id == action_id)
    if response_id is not None:
        query = query.filter(MediaFile.response_id == response_id)
    return query.order_by(MediaFile.created_at.desc()).all()


def delete_file_by_url(file_url: str) -> None:
    path = _resolve_upload_path(file_url)
    if path and path.is_file():
        try:
            path.unlink()
        except FileNotFoundError:
            return


def _resolve_upload_path(file_url: str) -> Path | None:
    if not file_url:
        return None
    prefix = "/uploads/"
    if not file_url.startswith(prefix):
        return None
    filename = file_url[len(prefix) :]
    candidate = (UPLOAD_DIR / filename).resolve()
    uploads_root = UPLOAD_DIR.resolve()
    try:
        candidate.relative_to(uploads_root)
    except ValueError:
        return None
    return candidate
