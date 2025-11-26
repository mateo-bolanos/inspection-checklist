from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.schemas.config import SeveritySLARead, SeveritySLAUpdate
from app.services import auth as auth_service
from app.services import config as config_service

router = APIRouter()


@router.get("/severity-sla", response_model=SeveritySLARead)
def read_severity_sla(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> SeveritySLARead:
    return config_service.get_severity_sla(db)


@router.put("/severity-sla", response_model=SeveritySLARead)
def update_severity_sla(
    payload: SeveritySLAUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> SeveritySLARead:
    try:
        return config_service.update_severity_sla(db, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

