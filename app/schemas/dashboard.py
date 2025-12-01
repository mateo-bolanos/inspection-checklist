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


class CompletionHealth(BaseModel):
    total: int
    completed: int
    open: int
    completion_rate: float


class IssueClosure(BaseModel):
    total: int
    closed: int
    open: int
    with_corrective_action: int
    closure_rate: float


class FailCategoryStat(BaseModel):
    label: str
    fail_count: int
    pass_count: int
    fail_rate: float


class MonthlyFailPoint(BaseModel):
    month: str
    fail_count: int


class HotspotStat(BaseModel):
    location: str
    issue_count: int


class InspectorLoad(BaseModel):
    inspector_id: str
    name: str
    inspection_count: int


class DuplicateSummary(BaseModel):
    duplicate_records: int
    days_with_duplicates: int
    max_duplicates_in_day: int


class DurationStats(BaseModel):
    average_minutes: float | None
    median_minutes: float | None
    max_minutes: float | None


class IssueDensity(BaseModel):
    average_issues: float | None
    max_issues: int | None
    inspections_with_issues: int


class CadenceStat(BaseModel):
    month: str
    inspections: int


class CalendarCell(BaseModel):
    date: str
    fail_count: int
    inspection_count: int


class PriorityDashboard(BaseModel):
    completion: CompletionHealth
    issue_closure: IssueClosure
    fail_categories: list[FailCategoryStat]
    monthly_fail_trend: list[MonthlyFailPoint]
    hotspots: list[HotspotStat]
    inspector_workload: list[InspectorLoad]
    duplicates: DuplicateSummary
    duration: DurationStats
    issue_density: IssueDensity
    cadence: list[CadenceStat]
    calendar_heatmap: list[CalendarCell]
    longest_gap_days: int
