from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.schemas.template import (
    ChecklistTemplateCreate,
    ChecklistTemplateRead,
    ChecklistTemplateUpdate,
    TemplateItemCreate,
    TemplateItemRead,
    TemplateItemUpdate,
    TemplateSectionCreate,
    TemplateSectionRead,
    TemplateSectionUpdate,
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
    return _get_template_or_404(db, template_id)


@router.put("/{template_id}", response_model=ChecklistTemplateRead)
def update_template(
    template_id: str,
    payload: ChecklistTemplateUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> ChecklistTemplateRead:
    template = _get_template_or_404(db, template_id)
    return template_service.update_template(db, template, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> Response:
    template = _get_template_or_404(db, template_id)
    template_service.delete_template(db, template)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/sections", response_model=TemplateSectionRead, status_code=status.HTTP_201_CREATED)
def create_section(
    template_id: str,
    payload: TemplateSectionCreate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> TemplateSectionRead:
    template = _get_template_or_404(db, template_id)
    return template_service.create_section(db, template, payload)


@router.put("/{template_id}/sections/{section_id}", response_model=TemplateSectionRead)
def update_section(
    template_id: str,
    section_id: str,
    payload: TemplateSectionUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> TemplateSectionRead:
    template = _get_template_or_404(db, template_id)
    section = _get_section_or_404(db, section_id, template.id)
    return template_service.update_section(db, section, payload)


@router.delete("/{template_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    template_id: str,
    section_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> Response:
    template = _get_template_or_404(db, template_id)
    section = _get_section_or_404(db, section_id, template.id)
    template_service.delete_section(db, section)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{template_id}/sections/{section_id}/items",
    response_model=TemplateItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    template_id: str,
    section_id: str,
    payload: TemplateItemCreate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> TemplateItemRead:
    template = _get_template_or_404(db, template_id)
    section = _get_section_or_404(db, section_id, template.id)
    return template_service.create_item(db, section, payload)


@router.put(
    "/{template_id}/sections/{section_id}/items/{item_id}",
    response_model=TemplateItemRead,
)
def update_item(
    template_id: str,
    section_id: str,
    item_id: str,
    payload: TemplateItemUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> TemplateItemRead:
    template = _get_template_or_404(db, template_id)
    section = _get_section_or_404(db, section_id, template.id)
    item = _get_item_or_404(db, item_id, section.id)
    return template_service.update_item(db, item, payload)


@router.delete("/{template_id}/sections/{section_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    template_id: str,
    section_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.require_role([UserRole.admin.value])),
) -> Response:
    template = _get_template_or_404(db, template_id)
    section = _get_section_or_404(db, section_id, template.id)
    item = _get_item_or_404(db, item_id, section.id)
    template_service.delete_item(db, item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_template_or_404(db: Session, template_id: str):
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


def _get_section_or_404(db: Session, section_id: str, template_id: str):
    section = template_service.get_section(db, section_id)
    if not section or section.template_id != template_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


def _get_item_or_404(db: Session, item_id: str, section_id: str):
    item = template_service.get_item(db, item_id)
    if not item or item.section_id != section_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
