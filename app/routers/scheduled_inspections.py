from __future__ import annotations

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.schemas.assignment import ScheduledInspectionRead
from app.services import assignments as assignment_service
from app.services import auth as auth_service

router = APIRouter()


@router.get("/scheduled-inspections", response_model=List[ScheduledInspectionRead])
def list_scheduled_inspections_endpoint(
    status: str | None = Query(default=None),
    assigned_to_id: str | None = Query(default=None, alias="assignedToId"),
    week_start: date | None = Query(default=None, alias="weekStart"),
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[ScheduledInspectionRead]:
    try:
        return assignment_service.list_scheduled_inspections(
            db,
            current_user,
            status=status,
            assigned_to_id=assigned_to_id,
            week_start=week_start,
        )
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/scheduler/generate",
    response_model=List[ScheduledInspectionRead],
    status_code=status.HTTP_201_CREATED,
)
def trigger_generation_endpoint(
    week_start: date | None = Query(default=None, alias="weekStart"),
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> List[ScheduledInspectionRead]:
    return assignment_service.generate_scheduled_inspections(db, target_week_start=week_start)
