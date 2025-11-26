from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import InspectionOrigin, UserRole
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.inspection import InspectionCreate, InspectionRead
from app.services import assignments as assignment_service
from app.services import auth as auth_service
from app.services import inspections as inspection_service

router = APIRouter()


@router.get("/", response_model=List[AssignmentRead])
def list_assignments_endpoint(
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[AssignmentRead]:
    return assignment_service.list_assignments(db, current_user, active=active)


@router.post("/", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> AssignmentRead:
    try:
        return assignment_service.create_assignment(db, current_user, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{assignment_id}/start", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
def start_assignment_inspection(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionRead:
    assignment = assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if current_user.role not in {UserRole.admin.value, UserRole.reviewer.value} and assignment.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to start this assignment")
    if not assignment.template_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment is missing a template")

    inspector_override = assignment.assigned_to_id if current_user.role in {UserRole.admin.value, UserRole.reviewer.value} else None
    scheduled = assignment_service.ensure_pending_schedule(db, assignment)
    payload = InspectionCreate(
        template_id=assignment.template_id,
        inspector_id=inspector_override,
        location=assignment.location,
        scheduled_inspection_id=scheduled.id if scheduled else None,
    )

    try:
        return inspection_service.create_inspection(
            db,
            current_user,
            payload,
            origin=InspectionOrigin.assignment,
        )
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
