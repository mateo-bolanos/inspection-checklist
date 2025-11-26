from __future__ import annotations

import mimetypes
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

STORAGE_DIR = Path("uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per attachment
ALLOWED_MIME_PREFIXES = ("image/",)
ALLOWED_STRICT_MIME_TYPES = {"application/pdf"}


def save_media_file(
    db: Session,
    *,
    content: bytes,
    original_name: str | None,
    response_id: str | None,
    action_id: int | None,
    uploaded_by: str | None,
    content_type: str | None,
) -> MediaFile:
    size = len(content)
    if size == 0:
        raise ValueError("File is empty")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 10 MB limit")
    mime_type = _detect_mime_type(content, content_type, original_name)
    if not _is_allowed_mime_type(mime_type):
        raise ValueError("Only image files and PDFs are allowed")

    suffix = _choose_suffix(original_name, mime_type)
    filename = f"{uuid.uuid4().hex}{suffix}"
    file_path = STORAGE_DIR / filename
    file_path.write_bytes(content)

    media_id = uuid.uuid4().hex
    media = MediaFile(
        id=media_id,
        response_id=response_id,
        action_id=action_id,
        storage_path=filename,
        mime_type=mime_type,
        size_bytes=size,
        original_name=original_name,
        file_url=_build_download_url(media_id),
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
        filters = [MediaFile.uploaded_by_id == user.id]
        filters.append(
            MediaFile.response.has(
                InspectionResponse.inspection.has(Inspection.inspector_id == user.id),
            )
        )
        filters.append(
            MediaFile.action.has(
                CorrectiveAction.inspection.has(Inspection.inspector_id == user.id),
            )
        )
        if user.role == UserRole.action_owner.value:
            filters.append(
                MediaFile.action.has(CorrectiveAction.assigned_to_id == user.id)
            )
        query = query.filter(or_(*filters))
    if action_id is not None:
        query = query.filter(MediaFile.action_id == action_id)
    if response_id is not None:
        query = query.filter(MediaFile.response_id == response_id)
    return query.order_by(MediaFile.created_at.desc()).all()


def get_media_file(
    db: Session,
    media_id: str,
) -> MediaFile | None:
    return (
        db.query(MediaFile)
        .options(
            selectinload(MediaFile.response).selectinload(InspectionResponse.inspection),
            selectinload(MediaFile.action).selectinload(CorrectiveAction.inspection),
            selectinload(MediaFile.uploaded_by),
        )
        .filter(MediaFile.id == media_id)
        .first()
    )


def delete_media_record(db: Session, media: MediaFile) -> None:
    """Remove the binary from disk and delete the row."""
    file_path = resolve_media_path(media)
    if file_path.is_file():
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
    db.delete(media)


def resolve_media_path(media: MediaFile) -> Path:
    candidate = (STORAGE_DIR / media.storage_path).resolve()
    root = STORAGE_DIR.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        candidate = root / Path(media.storage_path).name
    return candidate


def _detect_mime_type(content: bytes, declared_type: str | None, original_name: str | None) -> str:
    """Best-effort content sniffing to avoid trusting the browser-provided type."""
    detected_image = _detect_image_mime(content)
    if detected_image:
        return detected_image
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if declared_type:
        return declared_type.lower()
    if original_name:
        guessed, _ = mimetypes.guess_type(original_name)
        if guessed:
            return guessed.lower()
    return "application/octet-stream"


def _is_allowed_mime_type(mime_type: str) -> bool:
    return mime_type.startswith(ALLOWED_MIME_PREFIXES) or mime_type in ALLOWED_STRICT_MIME_TYPES


def _choose_suffix(original_name: str | None, mime_type: str) -> str:
    if original_name:
        suffix = Path(original_name).suffix
        if suffix:
            return suffix.lower()
    mapped = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
    }
    return mapped.get(mime_type, "")


def _build_download_url(media_id: str) -> str:
    return f"/files/{media_id}/download"


def _detect_image_mime(content: bytes) -> str | None:
    """Lightweight signature-based detection for common image formats."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith(b"BM"):
        return "image/bmp"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None
