from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.models.entities import ChecklistTemplate, TemplateItem, TemplateSection
from app.schemas.template import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    TemplateItemCreate,
    TemplateItemUpdate,
    TemplateSectionCreate,
    TemplateSectionUpdate,
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


def get_section(db: Session, section_id: str) -> TemplateSection | None:
    return (
        db.query(TemplateSection)
        .options(selectinload(TemplateSection.items))
        .filter(TemplateSection.id == section_id)
        .first()
    )


def create_section(
    db: Session, template: ChecklistTemplate, payload: TemplateSectionCreate
) -> TemplateSection:
    section = TemplateSection(
        title=payload.title,
        order_index=payload.order_index,
        template=template,
    )
    for item in payload.items:
        TemplateItem(
            prompt=item.prompt,
            is_required=item.is_required,
            order_index=item.order_index,
            section=section,
        )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def update_section(db: Session, section: TemplateSection, payload: TemplateSectionUpdate) -> TemplateSection:
    if payload.title is not None:
        section.title = payload.title
    if payload.order_index is not None:
        section.order_index = payload.order_index
    db.commit()
    db.refresh(section)
    return section


def delete_section(db: Session, section: TemplateSection) -> None:
    db.delete(section)
    db.commit()


def get_item(db: Session, item_id: str) -> TemplateItem | None:
    return db.query(TemplateItem).filter(TemplateItem.id == item_id).first()


def create_item(db: Session, section: TemplateSection, payload: TemplateItemCreate) -> TemplateItem:
    item = TemplateItem(
        prompt=payload.prompt,
        is_required=payload.is_required,
        order_index=payload.order_index,
        section=section,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: TemplateItem, payload: TemplateItemUpdate) -> TemplateItem:
    if payload.prompt is not None:
        item.prompt = payload.prompt
    if payload.is_required is not None:
        item.is_required = payload.is_required
    if payload.order_index is not None:
        item.order_index = payload.order_index
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: TemplateItem) -> None:
    db.delete(item)
    db.commit()
