from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone, timedelta
from statistics import median

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.models.entities import (
    Assignment,
    ActionStatus,
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
    PriorityDashboard,
    WeeklyInspectionKPIs,
    WeeklyPendingUser,
    CalendarCell,
    CadenceStat,
    CompletionHealth,
    DurationStats,
    DuplicateSummary,
    FailCategoryStat,
    HotspotStat,
    InspectorLoad,
    IssueClosure,
    IssueDensity,
    MonthlyFailPoint,
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


def _rate(part: int, total: int) -> float:
    return round((part / total) * 100, 2) if total else 0.0


def _month_floor(value: date) -> date:
    return date(value.year, value.month, 1)


def _months_ago(value: date, months: int) -> date:
    month = value.month - months
    year = value.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def get_priority_dashboard(
    db: Session,
    *,
    start: date | None,
    end: date | None,
    template_id: str | None,
    location: str | None,
    locations: list[str] | None,
    inspector_id: str | None,
    item_query: str | None,
    calendar_month: str | None,
) -> PriorityDashboard:
    """
    Data-backed priorities used by the Dashboards page. All metrics are derived from the live SQLite database.
    """

    today = date.today()
    end_date = end or today
    start_date = start or _months_ago(_month_floor(end_date), 11)

    month_window_start = _month_floor(start_date)
    month_window_end = end_date
    calendar_window_start = start_date
    calendar_window_end = end_date
    if calendar_month:
        try:
            cal_month_date = datetime.strptime(f"{calendar_month}-01", "%Y-%m-%d").date()
            calendar_window_start = cal_month_date
            next_month = cal_month_date.replace(day=28) + timedelta(days=4)
            calendar_window_end = next_month.replace(day=1) - timedelta(days=1)
        except ValueError:
            calendar_window_start = start_date
            calendar_window_end = end_date

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    base_inspection_filters = []
    if inspector_id:
        base_inspection_filters.append(Inspection.inspector_id == inspector_id)
    if template_id:
        base_inspection_filters.append(Inspection.template_id == template_id)
    location_terms = [location] if location else []
    if locations:
        location_terms.extend(locations)
    location_terms = [term for term in location_terms if term]
    if location_terms:
        lowered = [term.strip().lower() for term in location_terms]
        clauses = [func.lower(Inspection.location).ilike(f"%{term}%") for term in lowered]
        base_inspection_filters.append(clauses[0] if len(clauses) == 1 else or_(*clauses))

    item_filter_ids: set[int] = set()
    if item_query:
        item_rows = (
            db.query(func.distinct(InspectionResponse.inspection_id))
            .join(Inspection, InspectionResponse.inspection_id == Inspection.id)
            .join(TemplateItem, InspectionResponse.template_item_id == TemplateItem.id)
            .filter(func.lower(TemplateItem.prompt).like(f"%{item_query.strip().lower()}%"), *base_inspection_filters)
            .all()
        )
        item_filter_ids = {row[0] for row in item_rows}
        base_inspection_filters.append(Inspection.id.in_(item_filter_ids or [-1]))

    inspection_filters = [Inspection.started_at >= start_dt, Inspection.started_at <= end_dt, *base_inspection_filters]

    completed_statuses = [
        InspectionStatus.submitted.value,
        InspectionStatus.approved.value,
        InspectionStatus.rejected.value,
    ]
    total_inspections = db.query(func.count(Inspection.id)).filter(*inspection_filters).scalar() or 0
    completed_inspections = (
        db.query(func.count(Inspection.id))
        .filter(*inspection_filters, Inspection.status.in_(completed_statuses))
        .scalar()
        or 0
    )
    open_inspections = max(total_inspections - completed_inspections, 0)

    action_filters = []
    if template_id or location_terms or start_date or end_date or inspector_id or item_filter_ids:
        action_filters.append(CorrectiveAction.inspection_id == Inspection.id)
    if start_date or end_date:
        action_filters.extend([Inspection.started_at >= start_dt, Inspection.started_at <= end_dt])
    if template_id:
        action_filters.append(Inspection.template_id == template_id)
    if inspector_id:
        action_filters.append(Inspection.inspector_id == inspector_id)
    if location_terms:
        lowered_actions = [term.strip().lower() for term in location_terms]
        clauses = [func.lower(Inspection.location).ilike(f"%{term}%") for term in lowered_actions]
        action_filters.append(clauses[0] if len(clauses) == 1 else or_(*clauses))
    if item_filter_ids:
        action_filters.append(CorrectiveAction.inspection_id.in_(item_filter_ids))

    total_actions_query = db.query(CorrectiveAction.id)
    closed_actions_query = db.query(CorrectiveAction.id)
    if action_filters:
        total_actions_query = total_actions_query.join(Inspection).filter(*action_filters)
        closed_actions_query = closed_actions_query.join(Inspection).filter(*action_filters)
    total_actions = total_actions_query.count()
    closed_actions = (
        closed_actions_query.filter(CorrectiveAction.status == ActionStatus.closed.value).count()
    )
    open_actions = max(total_actions - closed_actions, 0)

    fail_rows = (
        db.query(
            TemplateItem.prompt.label("label"),
            func.count(InspectionResponse.id).label("total"),
            func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).label("fail_count"),
        )
        .join(InspectionResponse, InspectionResponse.template_item_id == TemplateItem.id)
        .join(Inspection, InspectionResponse.inspection_id == Inspection.id)
        .filter(*inspection_filters)
        .group_by(TemplateItem.prompt)
        .order_by(func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).desc())
        .limit(12)
        .all()
    )
    fail_categories: list[FailCategoryStat] = []
    for row in fail_rows:
        total = int(row.total or 0)
        fail_count = int(row.fail_count or 0)
        pass_count = max(total - fail_count, 0)
        label = row.label or "Unlabeled item"
        fail_categories.append(
            FailCategoryStat(
                label=label,
                fail_count=fail_count,
                pass_count=pass_count,
                fail_rate=_rate(fail_count, total),
            )
        )

    month_window_start_dt = datetime.combine(month_window_start, time.min)
    month_window_end_dt = datetime.combine(month_window_end, time.max)

    monthly_fail_rows = {
        row.month: int(row.fail_count or 0)
        for row in (
            db.query(
                func.strftime("%Y-%m", Inspection.started_at).label("month"),
                func.count(InspectionResponse.id).label("fail_count"),
            )
            .join(Inspection, InspectionResponse.inspection_id == Inspection.id)
            .filter(
                InspectionResponse.result == "fail",
                Inspection.started_at >= month_window_start_dt,
                Inspection.started_at <= month_window_end_dt,
                *base_inspection_filters,
            )
            .group_by("month")
            .order_by("month")
            .all()
        )
    }
    months_sequence: list[str] = []
    cursor = month_window_start
    while cursor <= month_window_end:
        months_sequence.append(cursor.strftime("%Y-%m"))
        # advance one month
        next_month = cursor.month + 1
        next_year = cursor.year
        if next_month == 13:
            next_month = 1
            next_year += 1
        cursor = date(next_year, next_month, 1)
    monthly_fail_trend = [
        MonthlyFailPoint(month=month, fail_count=monthly_fail_rows.get(month, 0)) for month in months_sequence
    ]

    hotspot_rows = (
        db.query(
            func.coalesce(func.nullif(func.trim(Inspection.location), ""), "Unspecified").label("location"),
            func.count(CorrectiveAction.id).label("issue_count"),
        )
        .join(Inspection, CorrectiveAction.inspection_id == Inspection.id)
        .filter(*inspection_filters)
        .group_by("location")
        .order_by(func.count(CorrectiveAction.id).desc())
        .limit(8)
        .all()
    )
    hotspots = [
        HotspotStat(location=row.location, issue_count=int(row.issue_count or 0))
        for row in hotspot_rows
        if row.issue_count
    ]

    inspector_rows = (
        db.query(
            User.id.label("inspector_id"),
            func.coalesce(func.nullif(func.trim(User.full_name), ""), User.email).label("name"),
            func.count(Inspection.id).label("inspection_count"),
        )
        .join(Inspection, Inspection.inspector_id == User.id)
        .filter(*inspection_filters)
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(Inspection.id).desc())
        .all()
    )
    inspector_workload = [
        InspectorLoad(
            inspector_id=row.inspector_id,
            name=row.name,
            inspection_count=int(row.inspection_count or 0),
        )
        for row in inspector_rows
    ]

    duplicate_rows = (
        db.query(
            func.date(Inspection.started_at).label("day"),
            InspectionResponse.inspection_id,
            InspectionResponse.template_item_id,
            func.count(InspectionResponse.id).label("response_count"),
        )
        .join(Inspection, InspectionResponse.inspection_id == Inspection.id)
        .filter(*inspection_filters)
        .group_by("day", InspectionResponse.inspection_id, InspectionResponse.template_item_id)
        .having(func.count(InspectionResponse.id) > 1)
        .all()
    )
    duplicates_by_day: dict[str, int] = defaultdict(int)
    duplicate_records = 0
    for row in duplicate_rows:
        extra = int(row.response_count or 0) - 1
        if extra > 0:
            duplicate_records += extra
            duplicates_by_day[row.day] += extra
    days_with_duplicates = len(duplicates_by_day)
    max_duplicates_in_day = max(duplicates_by_day.values()) if duplicates_by_day else 0

    duration_rows = (
        db.query(Inspection.started_at, Inspection.submitted_at)
        .filter(Inspection.submitted_at.isnot(None))
        .filter(*inspection_filters)
        .order_by(Inspection.started_at)
        .all()
    )
    durations_minutes: list[float] = []
    for started_at, submitted_at in duration_rows:
        if started_at and submitted_at:
            delta = submitted_at - started_at
            durations_minutes.append(round(delta.total_seconds() / 60, 2))
    duration_stats = DurationStats(
        average_minutes=round(sum(durations_minutes) / len(durations_minutes), 2) if durations_minutes else None,
        median_minutes=round(median(durations_minutes), 2) if durations_minutes else None,
        max_minutes=round(max(durations_minutes), 2) if durations_minutes else None,
    )

    issue_counts = [
        int(row.issue_count or 0)
        for row in db.query(
            CorrectiveAction.inspection_id, func.count(CorrectiveAction.id).label("issue_count")
        )
        .join(Inspection, CorrectiveAction.inspection_id == Inspection.id)
        .filter(*inspection_filters)
        .group_by(CorrectiveAction.inspection_id)
        .all()
    ]
    issue_density = IssueDensity(
        average_issues=round(sum(issue_counts) / len(issue_counts), 2) if issue_counts else None,
        max_issues=max(issue_counts) if issue_counts else None,
        inspections_with_issues=len(issue_counts),
    )

    cadence_counts = {
        row.month: int(row.count or 0)
        for row in (
            db.query(
                func.strftime("%Y-%m", Inspection.started_at).label("month"),
                func.count(Inspection.id).label("count"),
            )
            .filter(Inspection.started_at >= month_window_start_dt, Inspection.started_at <= month_window_end_dt, *base_inspection_filters)
            .group_by("month")
            .order_by("month")
            .all()
        )
    }
    cadence = [CadenceStat(month=month, inspections=cadence_counts.get(month, 0)) for month in months_sequence]

    calendar_rows = {
        row.day: (int(row.inspection_count or 0), int(row.fail_count or 0))
        for row in (
            db.query(
                func.date(Inspection.started_at).label("day"),
                func.count(func.distinct(Inspection.id)).label("inspection_count"),
                func.coalesce(func.sum(case((InspectionResponse.result == "fail", 1), else_=0)), 0).label("fail_count"),
            )
            .outerjoin(InspectionResponse, InspectionResponse.inspection_id == Inspection.id)
            .filter(
                Inspection.started_at >= calendar_window_start,
                Inspection.started_at <= datetime.combine(calendar_window_end, time.max),
                *inspection_filters,
            )
            .group_by("day")
            .order_by("day")
            .all()
        )
    }
    calendar_heatmap = []
    cursor_day = calendar_window_start
    while cursor_day <= calendar_window_end:
        day_str = cursor_day.isoformat()
        inspection_count, fail_count = calendar_rows.get(day_str, (0, 0))
        calendar_heatmap.append(
            CalendarCell(
                date=day_str,
                inspection_count=inspection_count,
                fail_count=fail_count,
            )
        )
        cursor_day += timedelta(days=1)

    inspection_dates = [
        row.started_at.date()
        for row in db.query(Inspection.started_at)
        .filter(Inspection.started_at.isnot(None))
        .filter(*inspection_filters)
        .order_by(Inspection.started_at)
        .all()
        if row.started_at
    ]
    longest_gap = 0
    for prev, curr in zip(inspection_dates, inspection_dates[1:]):
        gap = (curr - prev).days
        if gap > longest_gap:
            longest_gap = gap

    return PriorityDashboard(
        completion=CompletionHealth(
            total=total_inspections,
            completed=completed_inspections,
            open=open_inspections,
            completion_rate=_rate(completed_inspections, total_inspections),
        ),
        issue_closure=IssueClosure(
            total=total_actions,
            closed=closed_actions,
            open=open_actions,
            with_corrective_action=total_actions,
            closure_rate=_rate(closed_actions, total_actions),
        ),
        fail_categories=fail_categories,
        monthly_fail_trend=monthly_fail_trend,
        hotspots=hotspots,
        inspector_workload=inspector_workload,
        duplicates=DuplicateSummary(
            duplicate_records=duplicate_records,
            days_with_duplicates=days_with_duplicates,
            max_duplicates_in_day=max_duplicates_in_day,
        ),
        duration=duration_stats,
        issue_density=issue_density,
        cadence=cadence,
        calendar_heatmap=calendar_heatmap,
        longest_gap_days=longest_gap,
    )
