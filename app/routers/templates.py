from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.schemas.template import (
    ChecklistTemplateCreate,
    ChecklistTemplateRead,
    ChecklistTemplateUpdate,
)
from app.services import auth as auth_service
from app.services import templates as template_service

router = APIRouter()


@router.get("/", response_model=List[ChecklistTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> List[ChecklistTemplateRead]:
    return template_service.list_templates(db)


@router.post("/", response_model=ChecklistTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: ChecklistTemplateCreate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> ChecklistTemplateRead:
    return template_service.create_template(db, payload)


@router.get("/{template_id}", response_model=ChecklistTemplateRead)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> ChecklistTemplateRead:
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=ChecklistTemplateRead)
def update_template(
    template_id: str,
    payload: ChecklistTemplateUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> ChecklistTemplateRead:
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template_service.update_template(db, template, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> None:
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    template_service.delete_template(db, template)
