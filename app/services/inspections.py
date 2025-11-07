from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Inspection


def list_inspections(db: Session) -> list[Inspection]:
    return db.query(Inspection).all()
