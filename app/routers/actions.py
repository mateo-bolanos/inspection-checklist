from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.action import CorrectiveActionCreate, CorrectiveActionRead, CorrectiveActionUpdate
from app.services import actions as action_service
from app.services import auth as auth_service

router = APIRouter()


@router.get("/", response_model=List[CorrectiveActionRead])
def list_actions(
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> List[CorrectiveActionRead]:
    return action_service.list_actions(db, current_user)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    try:
        return action_service.update_action(db, action, payload, current_user)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
