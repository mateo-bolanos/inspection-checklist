from __future__ import annotations

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
