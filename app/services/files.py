from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.entities import MediaFile

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def save_media_file(
    db: Session,
    *,
    content: bytes,
    original_name: str | None,
    response_id: str | None,
    action_id: str | None,
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


def list_media_files(db: Session) -> list[MediaFile]:
    return db.query(MediaFile).order_by(MediaFile.created_at.desc()).all()
