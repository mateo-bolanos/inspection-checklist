from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TemplateItemBase(BaseModel):
    prompt: str
    is_required: bool = True
    requires_evidence_on_fail: bool = True
    order_index: int = 0


class TemplateItemCreate(TemplateItemBase):
    pass


class TemplateItemUpdate(BaseModel):
    prompt: str | None = None
    is_required: bool | None = None
    requires_evidence_on_fail: bool | None = None
    order_index: int | None = None


class TemplateItemRead(TemplateItemBase):
    id: str

    class Config:
        from_attributes = True


class TemplateSectionBase(BaseModel):
    title: str
    order_index: int = 0


class TemplateSectionCreate(TemplateSectionBase):
    items: List[TemplateItemCreate] = Field(default_factory=list)


class TemplateSectionUpdate(BaseModel):
    title: str | None = None
    order_index: int | None = None


class TemplateSectionRead(TemplateSectionBase):
    id: str
    items: List[TemplateItemRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChecklistTemplateBase(BaseModel):
    name: str
    description: str | None = None


class ChecklistTemplateCreate(ChecklistTemplateBase):
    sections: List[TemplateSectionCreate] = Field(default_factory=list)


class ChecklistTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ChecklistTemplateRead(ChecklistTemplateBase):
    id: str
    sections: List[TemplateSectionRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
