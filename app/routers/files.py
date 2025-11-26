from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.entities import CorrectiveAction, Inspection, InspectionResponse, MediaFile, User, UserRole
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
        _ensure_can_access_action(current_user, action)
    content = await file.read()
    try:
        media = files_service.save_media_file(
            db,
            content=content,
            original_name=file.filename,
            response_id=response_id,
            action_id=action_id,
            uploaded_by=current_user.id,
            content_type=file.content_type,
        )
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return media


@router.get("/{media_id}/download")
def download_media(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
) -> FileResponse:
    media = files_service.get_media_file(db, media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    _ensure_can_access_media(current_user, media)
    file_path = files_service.resolve_media_path(media)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    filename = media.original_name or file_path.name
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media.mime_type or "application/octet-stream",
    )


def _ensure_can_access_inspection(user: User, inspection: Inspection | None) -> None:
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    if user.role in {UserRole.admin.value, UserRole.reviewer.value}:
        return
    if inspection.inspector_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this inspection")


def _ensure_can_access_action(user: User, action: CorrectiveAction) -> None:
    if user.role in {UserRole.admin.value, UserRole.reviewer.value}:
        return
    if _action_owned_by_user(user, action):
        return
    _ensure_can_access_inspection(user, action.inspection)


def _ensure_can_access_media(user: User, media: MediaFile) -> None:
    if media.action and _action_owned_by_user(user, media.action):
        return
    inspection = None
    if media.response and media.response.inspection:
        inspection = media.response.inspection
    elif media.action and media.action.inspection:
        inspection = media.action.inspection
    if inspection:
        _ensure_can_access_inspection(user, inspection)
        return
    if user.role in {UserRole.admin.value, UserRole.reviewer.value}:
        return
    if media.uploaded_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this file")


def _action_owned_by_user(user: User, action: CorrectiveAction) -> bool:
    return user.role == UserRole.action_owner.value and action.assigned_to_id == user.id
