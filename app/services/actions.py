from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import CorrectiveAction


def list_actions(db: Session) -> list[CorrectiveAction]:
    return db.query(CorrectiveAction).all()
