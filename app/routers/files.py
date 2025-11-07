from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import CorrectiveAction, InspectionResponse
from app.schemas.media import MediaFileRead
from app.services import auth as auth_service
from app.services import files as files_service

router = APIRouter()


@router.get("/", response_model=List[MediaFileRead])
def list_media(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> List[MediaFileRead]:
    return files_service.list_media_files(db)


@router.post("/", response_model=MediaFileRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    response_id: str | None = None,
    action_id: str | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(auth_service.get_current_active_user),
) -> MediaFileRead:
    if not response_id and not action_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="response_id or action_id required")
    if response_id:
        response = db.query(InspectionResponse).filter(InspectionResponse.id == response_id).first()
        if not response:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if action_id:
        action = db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
        if not action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
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
