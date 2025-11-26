from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    total_inspections: int
    submitted_inspections: int
    approval_rate: float
    average_score: float | None


class ActionMetrics(BaseModel):
    open_by_severity: dict[str, int]
    overdue_actions: int


class ItemFailureMetric(BaseModel):
    item_id: str
    prompt: str
    fail_rate: float


class ItemsMetrics(BaseModel):
    failures: list[ItemFailureMetric]


class WeeklyInspectionKPIs(BaseModel):
    """Weekly scheduled-inspection KPIs (counts for Monday–Sunday)."""

    total_expected: int
    submitted: int
    approved: int
    pending: int
    overdue: int


class WeeklyPendingUser(BaseModel):
    """Pending/overdue scheduled inspections grouped per assignee."""

    user_id: str
    user_name: str
    pending_count: int
    overdue_count: int
    last_submission_at: datetime | None
