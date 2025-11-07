from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TemplateItemBase(BaseModel):
    prompt: str
    is_required: bool = True
    order_index: int = 0


class TemplateItemCreate(TemplateItemBase):
    pass


class TemplateItemRead(TemplateItemBase):
    id: str

    class Config:
        from_attributes = True


class TemplateSectionBase(BaseModel):
    title: str
    order_index: int = 0


class TemplateSectionCreate(TemplateSectionBase):
    items: List[TemplateItemCreate] = Field(default_factory=list)


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
