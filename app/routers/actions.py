from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.action import CorrectiveActionCreate, CorrectiveActionRead, CorrectiveActionUpdate
from app.services import actions as action_service
from app.services import auth as auth_service

router = APIRouter()


@router.get("/", response_model=List[CorrectiveActionRead])
def list_actions(
    assigned_to: str | None = Query(default=None, description="Filter by assignee ID"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
    location: str | None = Query(default=None, description="Filter by inspection location/department (contains match)"),
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[CorrectiveActionRead]:
    try:
        return action_service.list_actions(
            db,
            current_user,
            assigned_to=assigned_to,
            status=status_filter,
            location=location,
        )
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/", response_model=CorrectiveActionRead, status_code=status.HTTP_201_CREATED)
def create_action(
    payload: CorrectiveActionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> CorrectiveActionRead:
    try:
        return action_service.create_action(db, current_user, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{action_id}", response_model=CorrectiveActionRead)
def get_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> CorrectiveActionRead:
    action = action_service.get_action(db, action_id, current_user)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return action


@router.put("/{action_id}", response_model=CorrectiveActionRead)
def update_action(
    action_id: int,
    payload: CorrectiveActionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> CorrectiveActionRead:
    action = action_service.get_action(db, action_id, current_user)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    try:
        return action_service.update_action(db, action, payload, current_user)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/open-by-item/{template_item_id}", response_model=List[CorrectiveActionRead])
def list_open_actions_by_item(
    template_item_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[CorrectiveActionRead]:
    try:
        return action_service.list_open_actions_for_item(db, current_user, template_item_id)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
