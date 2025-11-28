from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.models.entities import ActionSeverity, ActionStatus
from app.schemas.auth import UserRead
from app.schemas.note import NoteEntryRead


class CorrectiveActionBase(BaseModel):
    title: str
    description: str | None = None
    severity: str = Field(default=ActionSeverity.medium.value)
    occurrence_severity: str | None = None
    injury_severity: str | None = None
    due_date: datetime | None = None
    assigned_to_id: str | None = None
    work_order_required: bool = False
    work_order_number: str | None = None


class CorrectiveActionCreate(CorrectiveActionBase):
    inspection_id: int
    response_id: str | None = None
    status: str = Field(default=ActionStatus.open.value)


class CorrectiveActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    occurrence_severity: str | None = None
    injury_severity: str | None = None
    due_date: datetime | None = None
    assigned_to_id: str | None = None
    status: str | None = None
    resolution_notes: str | None = None
    work_order_required: bool | None = None
    work_order_number: str | None = None


class CorrectiveActionRead(CorrectiveActionBase):
    id: int
    inspection_id: int
    response_id: str | None = None
    status: str
    inspection_location: str | None = None
    inspection_template_name: str | None = None
    assignee: UserRead | None = None
    created_at: datetime
    closed_at: datetime | None = None
    resolution_notes: str | None = None
    started_by: UserRead
    closed_by: UserRead | None = None
    media_urls: List[str] = Field(default_factory=list)
    note_entries: List[NoteEntryRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
