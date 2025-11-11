from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.schemas.auth import UserRead


class InspectionBase(BaseModel):
    template_id: str
    location: str | None = None
    notes: str | None = None


class InspectionCreate(InspectionBase):
    inspector_id: str | None = None


class InspectionUpdate(BaseModel):
    location: str | None = None
    notes: str | None = None
    status: str | None = None


class InspectionRead(InspectionBase):
    id: int
    inspector_id: str
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    overall_score: float | None = None
    created_by: UserRead

    class Config:
        from_attributes = True


class InspectionDetail(InspectionRead):
    responses: List["InspectionResponseRead"] = Field(default_factory=list)


class InspectionResponseBase(BaseModel):
    template_item_id: str
    result: str
    note: str | None = None
    media_urls: List[str] = Field(default_factory=list)


class InspectionResponseCreate(InspectionResponseBase):
    pass


class InspectionResponseUpdate(BaseModel):
    result: str | None = None
    note: str | None = None
    media_urls: List[str] | None = None


class InspectionResponseRead(InspectionResponseBase):
    id: str
    inspection_id: int

    class Config:
        from_attributes = True


InspectionDetail.model_rebuild()
