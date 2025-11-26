from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.entities import (
    Assignment,
    CorrectiveAction,
    Inspection,
    InspectionResponse,
    InspectionStatus,
    ScheduledInspection,
    TemplateItem,
    User,
)
from app.schemas.dashboard import (
    ActionMetrics,
    ItemsMetrics,
    ItemFailureMetric,
    OverviewMetrics,
    WeeklyInspectionKPIs,
    WeeklyPendingUser,
)


def get_overview_metrics(db: Session) -> OverviewMetrics:
    total_inspections = db.query(func.count(Inspection.id)).scalar() or 0
    submitted_inspections = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status.in_([InspectionStatus.submitted.value, InspectionStatus.approved.value, InspectionStatus.rejected.value]))
        .scalar()
        or 0
    )
    approved_inspections = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status == InspectionStatus.approved.value)
        .scalar()
        or 0
    )
    average_score = db.query(func.avg(Inspection.overall_score)).scalar()
    approval_rate = 0.0
    if submitted_inspections:
        approval_rate = round((approved_inspections / submitted_inspections) * 100, 2)
    return OverviewMetrics(
        total_inspections=total_inspections,
        submitted_inspections=submitted_inspections,
        approval_rate=approval_rate,
        average_score=round(float(average_score), 2) if average_score is not None else None,
    )


def get_action_metrics(db: Session) -> ActionMetrics:
    open_actions = (
        db.query(CorrectiveAction.severity, func.count(CorrectiveAction.id))
        .filter(CorrectiveAction.status != "closed")
        .group_by(CorrectiveAction.severity)
        .all()
    )
    open_by_severity: dict[str, int] = defaultdict(int)
    for severity, count in open_actions:
        open_by_severity[severity] = count

    now = datetime.now(timezone.utc)
    overdue_actions = (
        db.query(func.count(CorrectiveAction.id))
        .filter(
            CorrectiveAction.status != "closed",
            CorrectiveAction.due_date.isnot(None),
            CorrectiveAction.due_date < now,
        )
        .scalar()
        or 0
    )
    return ActionMetrics(open_by_severity=dict(open_by_severity), overdue_actions=overdue_actions)


def get_item_failure_metrics(db: Session, limit: int = 5) -> ItemsMetrics:
    rows = (
        db.query(
            TemplateItem.id,
            TemplateItem.prompt,
            func.count(InspectionResponse.id).label("total"),
            func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).label("failures"),
        )
        .join(InspectionResponse, InspectionResponse.template_item_id == TemplateItem.id)
        .group_by(TemplateItem.id)
        .order_by(func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).desc())
        .limit(limit)
        .all()
    )
    failures: list[ItemFailureMetric] = []
    for item_id, prompt, total, fail_count in rows:
        if not total:
            continue
        rate = round((fail_count or 0) / total * 100, 2)
        failures.append(ItemFailureMetric(item_id=item_id, prompt=prompt, fail_rate=rate))
    return ItemsMetrics(failures=failures)


def get_weekly_inspection_kpis(db: Session, start_date: date, end_date: date) -> WeeklyInspectionKPIs:
    """
    Aggregate scheduled-inspection counts for a calendar week (Monday–Sunday inclusive).
    """

    status_submitted = func.sum(case((ScheduledInspection.status == "completed", 1), else_=0))
    status_pending = func.sum(case((ScheduledInspection.status == "pending", 1), else_=0))
    status_overdue = func.sum(case((ScheduledInspection.status == "overdue", 1), else_=0))

    window_start = datetime.combine(start_date, time.min)
    window_end = datetime.combine(end_date, time.max)

    row = (
        db.query(
            func.count(ScheduledInspection.id).label("total_expected"),
            status_submitted.label("submitted"),
            status_pending.label("pending"),
            status_overdue.label("overdue"),
        )
        .filter(ScheduledInspection.due_at >= window_start, ScheduledInspection.due_at <= window_end)
        .first()
    )

    total_expected = int(row.total_expected or 0) if row else 0
    submitted = int(row.submitted or 0) if row else 0
    pending = int(row.pending or 0) if row else 0
    overdue = int(row.overdue or 0) if row else 0
    approved = (
        db.query(func.count(Inspection.id))
        .join(ScheduledInspection, Inspection.scheduled_inspection_id == ScheduledInspection.id)
        .filter(
            ScheduledInspection.due_at >= window_start,
            ScheduledInspection.due_at <= window_end,
            Inspection.status == InspectionStatus.approved.value,
        )
        .scalar()
        or 0
    )
    approved = int(approved)

    active_assignments = (
        db.query(func.count(Assignment.id))
        .filter(
            Assignment.active.is_(True),
            func.lower(Assignment.frequency) == "weekly",
        )
        .scalar()
        or 0
    )
    active_assignments = int(active_assignments)
    if total_expected == 0 and active_assignments > 0:
        pending = max(pending, active_assignments)
    total_expected = max(total_expected, active_assignments)

    return WeeklyInspectionKPIs(
        total_expected=total_expected,
        submitted=submitted,
        approved=approved,
        pending=pending,
        overdue=overdue,
    )


def get_weekly_pending_by_user(db: Session, start_date: date, end_date: date) -> list[WeeklyPendingUser]:
    """
    Return per-user counts of pending/overdue scheduled inspections for the week and their latest submission timestamp.
    """

    window_start = datetime.combine(start_date, time.min)
    window_end = datetime.combine(end_date, time.max)
    pending_expr = func.sum(case((ScheduledInspection.status == "pending", 1), else_=0))
    overdue_expr = func.sum(case((ScheduledInspection.status == "overdue", 1), else_=0))

    last_submission_sq = (
        db.query(
            Assignment.assigned_to_id.label("user_id"),
            func.max(Inspection.submitted_at).label("last_submission_at"),
        )
        .join(ScheduledInspection, ScheduledInspection.assignment_id == Assignment.id)
        .join(Inspection, Inspection.scheduled_inspection_id == ScheduledInspection.id)
        .filter(Inspection.submitted_at.isnot(None))
        .group_by(Assignment.assigned_to_id)
        .subquery()
    )

    rows = (
        db.query(
            User.id.label("user_id"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            pending_expr.label("pending_count"),
            overdue_expr.label("overdue_count"),
            last_submission_sq.c.last_submission_at,
        )
        .join(Assignment, Assignment.assigned_to_id == User.id)
        .join(ScheduledInspection, ScheduledInspection.assignment_id == Assignment.id)
        .outerjoin(last_submission_sq, last_submission_sq.c.user_id == User.id)
        .filter(
            ScheduledInspection.due_at >= window_start,
            ScheduledInspection.due_at <= window_end,
        )
        .group_by(
            User.id,
            User.full_name,
            User.email,
            last_submission_sq.c.last_submission_at,
        )
        .having((pending_expr + overdue_expr) > 0)  # type: ignore[operator]
        .order_by(
            overdue_expr.desc(),
            pending_expr.desc(),
            func.coalesce(func.nullif(func.trim(User.full_name), ""), User.email).asc(),
        )
        .all()
    )

    result: list[WeeklyPendingUser] = []
    for row in rows:
        full_name = (row.full_name or "").strip()
        display_name = full_name if full_name else row.email
        result.append(
            WeeklyPendingUser(
                user_id=row.user_id,
                user_name=display_name,
                pending_count=int(row.pending_count or 0),
                overdue_count=int(row.overdue_count or 0),
                last_submission_at=row.last_submission_at,
            )
        )
    return result
