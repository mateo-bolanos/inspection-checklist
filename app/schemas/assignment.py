from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.auth import UserRead


class AssignmentBase(BaseModel):
    assigned_to_id: str
    template_id: str | None = None
    location: str | None = None
    frequency: Literal["daily", "weekly", "monthly"] = Field(default="weekly")
    active: bool = Field(default=True)
    start_due_at: datetime
    end_date: date | None = None


class AssignmentCreate(AssignmentBase):
    template_id: str


class AssignmentRead(AssignmentBase):
    id: int
    template_name: str | None = None
    assignee: UserRead
    current_week_completed: bool = Field(default=False)

    class Config:
        from_attributes = True


class ScheduledInspectionRead(BaseModel):
    id: int
    assignment_id: int
    period_start: date
    due_at: datetime
    status: str
    generated_at: datetime
    assignment: AssignmentRead

    class Config:
        from_attributes = True
