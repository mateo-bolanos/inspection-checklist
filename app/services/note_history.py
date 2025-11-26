from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import CorrectiveActionNote, InspectionNote, InspectionResponseNote


def _normalized(value: str | None) -> str:
    return (value or "").strip()


def add_inspection_note(db: Session, inspection_id: int, author_id: str, body: str | None) -> InspectionNote | None:
    content = _normalized(body)
    if not content:
        return None
    entry = InspectionNote(inspection_id=inspection_id, author_id=author_id, body=content)
    db.add(entry)
    db.flush()
    return entry


def add_response_note(db: Session, response_id: str, author_id: str, body: str | None) -> InspectionResponseNote | None:
    content = _normalized(body)
    if not content:
        return None
    entry = InspectionResponseNote(response_id=response_id, author_id=author_id, body=content)
    db.add(entry)
    db.flush()
    return entry


def add_action_note(db: Session, action_id: int, author_id: str, body: str | None) -> CorrectiveActionNote | None:
    content = _normalized(body)
    if not content:
        return None
    entry = CorrectiveActionNote(action_id=action_id, author_id=author_id, body=content)
    db.add(entry)
    db.flush()
    return entry
