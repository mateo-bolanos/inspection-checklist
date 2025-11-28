from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, model_validator

from app.models.entities import InspectionOrigin
from app.schemas.auth import UserRead
from app.schemas.note import NoteEntryRead


class InspectionMutableFields(BaseModel):
    location: str | None = None
    location_id: int | None = None
    notes: str | None = None


class InspectionCreate(InspectionMutableFields):
    template_id: str | None = None
    inspector_id: str | None = None
    scheduled_inspection_id: int | None = None

    @model_validator(mode="after")
    def validate_template_or_schedule(self) -> "InspectionCreate":
        if self.scheduled_inspection_id is None and not self.template_id:
            raise ValueError("Template is required when inspection is not assigned")
        return self


class InspectionUpdate(InspectionMutableFields):
    status: str | None = None


class InspectionRead(InspectionMutableFields):
    template_id: str
    inspection_origin: InspectionOrigin
    id: int
    inspector_id: str
    scheduled_inspection_id: int | None = None
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    rejected_at: datetime | None = None
    overall_score: float | None = None
    rejection_reason: str | None = None
    rejected_by: UserRead | None = None
    created_by: UserRead

    class Config:
        from_attributes = True


class InspectionDetail(InspectionRead):
    responses: List["InspectionResponseRead"] = Field(default_factory=list)
    note_entries: List[NoteEntryRead] = Field(default_factory=list)
    rejection_entries: List["InspectionRejectionEntryRead"] = Field(default_factory=list)


class InspectionReject(BaseModel):
    reason: str
    follow_up_instructions: str | None = None
    item_ids: List[str] | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "InspectionReject":
        if not (self.reason or "").strip():
            raise ValueError("Rejection reason is required")
        if self.item_ids is not None and len(self.item_ids) == 0:
            raise ValueError("At least one item must be selected when item_ids are provided")
        return self


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
    note_entries: List[NoteEntryRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InspectionRejectionEntryRead(BaseModel):
    id: int
    inspection_id: int
    template_item_id: str | None = None
    reason: str
    follow_up_instructions: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    created_by: UserRead

    class Config:
        from_attributes = True


InspectionDetail.model_rebuild()
