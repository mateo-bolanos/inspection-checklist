from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.schemas.location import LocationCreate, LocationRead
from app.services import auth as auth_service
from app.services import locations as locations_service

router = APIRouter()


@router.get("/", response_model=List[LocationRead])
def list_locations(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> List[LocationRead]:
    return locations_service.list_locations(db)


@router.post("/", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> LocationRead:
    try:
        return locations_service.create_location(db, payload)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
