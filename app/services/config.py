from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import SeveritySLA
from app.schemas.config import SeveritySLAUpdate

DEFAULT_SLA_VALUES = {
    "low_days": 30,
    "medium_days": 7,
    "high_days": 1,
}


def get_severity_sla(db: Session) -> SeveritySLA:
    sla = db.query(SeveritySLA).order_by(SeveritySLA.id.asc()).first()
    if not sla:
        sla = SeveritySLA(**DEFAULT_SLA_VALUES)
        db.add(sla)
        db.commit()
        db.refresh(sla)
    return sla


def update_severity_sla(db: Session, payload: SeveritySLAUpdate) -> SeveritySLA:
    sla = get_severity_sla(db)
    for field in ("low_days", "medium_days", "high_days"):
        value = getattr(payload, field)
        if value is not None:
            setattr(sla, field, value)
    db.commit()
    db.refresh(sla)
    return sla
