from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.models.entities import ChecklistTemplate, TemplateItem, TemplateSection
from app.schemas.template import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
)


def list_templates(db: Session) -> list[ChecklistTemplate]:
    return (
        db.query(ChecklistTemplate)
        .options(
            selectinload(ChecklistTemplate.sections).selectinload(TemplateSection.items),
        )
        .all()
    )


def get_template(db: Session, template_id: str) -> ChecklistTemplate | None:
    return (
        db.query(ChecklistTemplate)
        .options(
            selectinload(ChecklistTemplate.sections).selectinload(TemplateSection.items),
        )
        .filter(ChecklistTemplate.id == template_id)
        .first()
    )


def create_template(db: Session, payload: ChecklistTemplateCreate) -> ChecklistTemplate:
    template = ChecklistTemplate(name=payload.name, description=payload.description)
    for section_data in payload.sections:
        section = TemplateSection(
            title=section_data.title,
            order_index=section_data.order_index,
            template=template,
        )
        for item_data in section_data.items:
            TemplateItem(
                prompt=item_data.prompt,
                is_required=item_data.is_required,
                order_index=item_data.order_index,
                section=section,
            )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session, template: ChecklistTemplate, payload: ChecklistTemplateUpdate
) -> ChecklistTemplate:
    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: ChecklistTemplate) -> None:
    db.delete(template)
    db.commit()
