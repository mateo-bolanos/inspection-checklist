from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.entities import CorrectiveAction, Inspection, InspectionResponse, User, UserRole
from app.schemas.media import MediaFileRead
from app.services import auth as auth_service
from app.services import files as files_service

router = APIRouter()


@router.get("/", response_model=List[MediaFileRead])
def list_media(
    response_id: str | None = None,
    action_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
) -> List[MediaFileRead]:
    return files_service.list_media_files(
        db,
        current_user,
        action_id=action_id,
        response_id=response_id,
    )


@router.post("/", response_model=MediaFileRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    response_id: str | None = None,
    action_id: int | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
) -> MediaFileRead:
    if not response_id and not action_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="response_id or action_id required")
    if response_id:
        response = (
            db.query(InspectionResponse)
            .options(selectinload(InspectionResponse.inspection))
            .filter(InspectionResponse.id == response_id)
            .first()
        )
        if not response:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
        _ensure_can_access_inspection(current_user, response.inspection)
    if action_id:
        action = (
            db.query(CorrectiveAction)
            .options(selectinload(CorrectiveAction.inspection))
            .filter(CorrectiveAction.id == action_id)
            .first()
        )
        if not action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
        _ensure_can_access_inspection(current_user, action.inspection)
    content = await file.read()
    media = files_service.save_media_file(
        db,
        content=content,
        original_name=file.filename,
        response_id=response_id,
        action_id=action_id,
        uploaded_by=current_user.id,
    )
    return media


def _ensure_can_access_inspection(user: User, inspection: Inspection | None) -> None:
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    if user.role in {UserRole.admin.value, UserRole.reviewer.value}:
        return
    if inspection.inspector_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this inspection")
