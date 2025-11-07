from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User, UserRole
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetail,
    InspectionRead,
    InspectionResponseCreate,
    InspectionResponseRead,
    InspectionResponseUpdate,
    InspectionUpdate,
)
from app.services import auth as auth_service
from app.services import inspections as inspection_service
from app.services import reports as report_service

router = APIRouter()


@router.get("/", response_model=List[InspectionRead])
def list_inspections(
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[InspectionRead]:
    return inspection_service.list_inspections(db, current_user)


@router.post("/", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionRead:
    try:
        return inspection_service.create_inspection(db, current_user, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{inspection_id}", response_model=InspectionDetail)
def get_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionDetail:
    return _get_inspection_or_404(db, inspection_id, current_user)


@router.put("/{inspection_id}", response_model=InspectionRead)
def update_inspection(
    inspection_id: str,
    payload: InspectionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    try:
        return inspection_service.update_inspection(db, inspection, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{inspection_id}/submit", response_model=InspectionRead)
def submit_inspection_endpoint(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    _ensure_owner_or_admin(inspection, current_user)
    try:
        return inspection_service.submit_inspection(db, inspection)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{inspection_id}/approve", response_model=InspectionRead)
def approve_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> InspectionRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    try:
        return inspection_service.approve_inspection(db, inspection)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{inspection_id}/reject", response_model=InspectionRead)
def reject_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> InspectionRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    try:
        return inspection_service.reject_inspection(db, inspection)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{inspection_id}/export")
def export_inspection(
    inspection_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
):
    inspection = inspection_service.get_inspection(db, inspection_id, current_user)
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    summary = report_service.build_inspection_summary(inspection)
    if format.lower() == "pdf":
        pdf_bytes = report_service.render_pdf(summary)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="inspection-{inspection_id}.pdf"'},
        )
    return JSONResponse(summary)


@router.get("/{inspection_id}/responses", response_model=List[InspectionResponseRead])
def list_responses(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[InspectionResponseRead]:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    return inspection.responses


@router.post(
    "/{inspection_id}/responses",
    response_model=InspectionResponseRead,
    status_code=status.HTTP_201_CREATED,
)
def add_response(
    inspection_id: str,
    payload: InspectionResponseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionResponseRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    try:
        return inspection_service.create_response(db, inspection, payload, current_user)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{inspection_id}/responses/{response_id}", response_model=InspectionResponseRead)
def update_response(
    inspection_id: str,
    response_id: str,
    payload: InspectionResponseUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> InspectionResponseRead:
    inspection = _get_inspection_or_404(db, inspection_id, current_user)
    response = inspection_service.get_response(db, response_id, current_user)
    if not response or response.inspection_id != inspection.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    return inspection_service.update_response(db, response, payload, current_user)


def _get_inspection_or_404(db: Session, inspection_id: str, user: User) -> InspectionDetail:
    inspection = inspection_service.get_inspection(db, inspection_id, user)
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection


def _ensure_owner_or_admin(inspection: InspectionDetail, user: User) -> None:
    if user.role in {UserRole.admin.value, UserRole.reviewer.value}:
        return
    if inspection.inspector_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can submit inspection")
