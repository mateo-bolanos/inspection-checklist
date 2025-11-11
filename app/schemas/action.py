from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.entities import ActionSeverity, ActionStatus
from app.schemas.auth import UserRead


class CorrectiveActionBase(BaseModel):
    title: str
    description: str | None = None
    severity: str = Field(default=ActionSeverity.medium.value)
    due_date: datetime | None = None
    assigned_to_id: str | None = None


class CorrectiveActionCreate(CorrectiveActionBase):
    inspection_id: int
    response_id: str | None = None
    status: str = Field(default=ActionStatus.open.value)


class CorrectiveActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    due_date: datetime | None = None
    assigned_to_id: str | None = None
    status: str | None = None
    resolution_notes: str | None = None


class CorrectiveActionRead(CorrectiveActionBase):
    id: int
    inspection_id: int
    response_id: str | None = None
    status: str
    created_at: datetime
    closed_at: datetime | None = None
    resolution_notes: str | None = None
    started_by: UserRead
    closed_by: UserRead | None = None

    class Config:
        from_attributes = True
