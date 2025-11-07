from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CorrectiveActionBase(BaseModel):
    title: str
    description: str | None = None
    severity: str = "medium"
    due_date: datetime | None = None
    assigned_to_id: str | None = None
    status: str = "open"


class CorrectiveActionCreate(CorrectiveActionBase):
    inspection_id: str
    response_id: str | None = None


class CorrectiveActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    due_date: datetime | None = None
    assigned_to_id: str | None = None
    status: str | None = None


class CorrectiveActionRead(CorrectiveActionBase):
    id: str
    inspection_id: str
    response_id: str | None = None
    created_at: datetime
    closed_at: datetime | None = None

    class Config:
        from_attributes = True
