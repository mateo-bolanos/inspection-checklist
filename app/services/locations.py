from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import Location
from app.schemas.location import LocationCreate


def list_locations(db: Session) -> list[Location]:
    return db.query(Location).order_by(func.lower(Location.name)).all()


def get_location_by_id(db: Session, location_id: int) -> Location | None:
    return db.query(Location).filter(Location.id == location_id).first()


def get_location_by_name(db: Session, name: str | None) -> Location | None:
    normalized = _normalize_name(name)
    if not normalized:
        return None
    return (
        db.query(Location)
        .filter(func.lower(Location.name) == normalized.lower())
        .first()
    )


def create_location(db: Session, payload: LocationCreate) -> Location:
    normalized = _normalize_name(payload.name)
    if not normalized:
        raise ValueError("Location name is required")

    existing = get_location_by_name(db, normalized)
    if existing:
        raise ValueError("Location already exists")

    location = Location(name=normalized)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def ensure_location_by_name(
    db: Session,
    name: str | None,
    *,
    create_if_missing: bool,
    auto_commit: bool = True,
) -> Location | None:
    normalized = _normalize_name(name)
    if not normalized:
        return None

    location = get_location_by_name(db, normalized)
    if location:
        return location

    if not create_if_missing:
        return None

    location = Location(name=normalized)
    db.add(location)
    if auto_commit:
        db.commit()
        db.refresh(location)
    else:
        db.flush()
        db.refresh(location)
    return location


def _normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
