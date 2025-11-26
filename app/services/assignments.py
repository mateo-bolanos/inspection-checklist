from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.profile import is_company_profile
from app.models.entities import Assignment, ChecklistTemplate, ScheduledInspection, User, UserRole
from app.schemas.assignment import AssignmentCreate
from app.services import email as email_service
from app.services.notification_utils import build_frontend_url, format_date, format_datetime

DAILY_FREQUENCY = "daily"
WEEKLY_FREQUENCY = "weekly"
MONTHLY_FREQUENCY = "monthly"
VALID_FREQUENCIES = {DAILY_FREQUENCY, WEEKLY_FREQUENCY, MONTHLY_FREQUENCY}
DEFAULT_GENERATION_HORIZON_DAYS = 30

SCHEDULED_PENDING = "pending"
SCHEDULED_COMPLETED = "completed"
SCHEDULED_OVERDUE = "overdue"
VALID_SCHEDULED_STATUSES = {SCHEDULED_PENDING, SCHEDULED_COMPLETED, SCHEDULED_OVERDUE}


def list_assignments(db: Session, current_user: User, active: bool | None = None) -> list[Assignment]:
    query = (
        db.query(Assignment)
        .options(selectinload(Assignment.assignee), selectinload(Assignment.template))
        .order_by(Assignment.id.desc())
    )
    if active is not None:
        query = query.filter(Assignment.active.is_(active))
    if current_user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.filter(Assignment.assigned_to_id == current_user.id)
    assignments = query.all()
    _annotate_current_week_completion(db, assignments)
    return assignments

def get_assignment(db: Session, assignment_id: int) -> Assignment | None:
    return (
        db.query(Assignment)
        .options(selectinload(Assignment.assignee), selectinload(Assignment.template))
        .filter(Assignment.id == assignment_id)
        .first()
    )

def create_assignment(db: Session, current_user: User, payload: AssignmentCreate) -> Assignment:
    _require_admin(current_user)
    assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
    if not assignee:
        raise ValueError("Assigned user not found")
    template = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == payload.template_id).first()
    if not template:
        raise ValueError("Template not found")
    frequency = _normalize_frequency(payload.frequency)
    if is_company_profile() and frequency != WEEKLY_FREQUENCY:
        raise ValueError("Weekly frequency is enforced for company assignments")
    if is_company_profile():
        frequency = WEEKLY_FREQUENCY
    start_due_at = _normalize_due_datetime(payload.start_due_at)
    assignment = Assignment(
        assigned_to_id=payload.assigned_to_id,
        template_id=template.id,
        location=payload.location,
        frequency=frequency,
        active=payload.active,
        start_due_at=start_due_at,
        end_date=payload.end_date,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_scheduled_inspections(
    db: Session,
    current_user: User,
    *,
    status: str | None = None,
    assigned_to_id: str | None = None,
    week_start: date | None = None,
) -> list[ScheduledInspection]:
    base_date = week_start or datetime.utcnow().date()
    normalized_week = _normalize_week_start(base_date)
    window_start = datetime.combine(normalized_week, time.min)
    window_end = datetime.combine(normalized_week + timedelta(days=6), time.max)
    query = (
        db.query(ScheduledInspection)
        .options(selectinload(ScheduledInspection.assignment).selectinload(Assignment.assignee))
        .filter(ScheduledInspection.due_at >= window_start, ScheduledInspection.due_at <= window_end)
        .order_by(ScheduledInspection.due_at.asc())
    )
    if status:
        if status not in VALID_SCHEDULED_STATUSES:
            raise ValueError("Invalid status filter")
        query = query.filter(ScheduledInspection.status == status)
    if assigned_to_id:
        query = query.join(Assignment).filter(Assignment.assigned_to_id == assigned_to_id)
    elif current_user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.join(Assignment).filter(Assignment.assigned_to_id == current_user.id)
    return query.all()


def generate_scheduled_inspections(db: Session, target_week_start: date | None = None) -> list[ScheduledInspection]:
    """
    Create scheduled inspections for active assignments within the requested window.
    When no window is provided, the generator ensures each assignment has coverage for the upcoming horizon.
    """

    window_start, window_end = _resolve_generation_window(target_week_start)
    assignments: Iterable[Assignment] = (
        db.query(Assignment)
        .options(selectinload(Assignment.assignee))
        .filter(Assignment.active.is_(True))
        .all()
    )
    last_due_rows = (
        db.query(
            ScheduledInspection.assignment_id,
            func.max(ScheduledInspection.due_at).label("last_due_at"),
        )
        .group_by(ScheduledInspection.assignment_id)
        .all()
    )
    last_due_by_assignment = {row.assignment_id: row.last_due_at for row in last_due_rows}

    created: list[ScheduledInspection] = []
    updates_made = False
    now = datetime.utcnow()

    for assignment in assignments:
        frequency = _normalize_frequency(assignment.frequency)
        last_due = last_due_by_assignment.get(assignment.id)
        seed = (
            _advance_due_at(last_due, frequency) if last_due else _normalize_due_datetime(assignment.start_due_at)
        )
        next_due = _next_due_from_seed(seed, frequency, window_start, assignment.end_date)
        while next_due and next_due <= window_end:
            scheduled = ScheduledInspection(
                assignment_id=assignment.id,
                assignment=assignment,
                period_start=_period_start_for_due(next_due, frequency),
                due_at=next_due,
                status=SCHEDULED_PENDING,
                generated_at=now,
            )
            db.add(scheduled)
            created.append(scheduled)
            updates_made = True
            last_due_by_assignment[assignment.id] = next_due
            seed = _advance_due_at(next_due, frequency)
            next_due = _next_due_from_seed(seed, frequency, window_start, assignment.end_date)
        if assignment.end_date and next_due is None and assignment.active:
            assignment.active = False
            updates_made = True

    if created or updates_made:
        db.commit()
        if created:
            for scheduled in created:
                db.refresh(scheduled)
            for scheduled in created:
                _notify_assignment_created(scheduled)
    return created


def ensure_pending_schedule(db: Session, assignment: Assignment) -> ScheduledInspection | None:
    scheduled = (
        db.query(ScheduledInspection)
        .filter(
            ScheduledInspection.assignment_id == assignment.id,
            ScheduledInspection.status.in_([SCHEDULED_PENDING, SCHEDULED_OVERDUE]),
        )
        .order_by(ScheduledInspection.due_at.asc())
        .first()
    )
    if scheduled:
        return scheduled
    reference_date = min(datetime.utcnow().date(), assignment.start_due_at.date())
    generate_scheduled_inspections(db, target_week_start=_normalize_week_start(reference_date))
    return (
        db.query(ScheduledInspection)
        .filter(
            ScheduledInspection.assignment_id == assignment.id,
            ScheduledInspection.status.in_([SCHEDULED_PENDING, SCHEDULED_OVERDUE]),
        )
        .order_by(ScheduledInspection.due_at.asc())
        .first()
    )


def mark_scheduled_completed(db: Session, scheduled_inspection_id: int, *, commit: bool = True) -> None:
    scheduled = db.query(ScheduledInspection).filter(ScheduledInspection.id == scheduled_inspection_id).first()
    if not scheduled:
        return
    scheduled.status = SCHEDULED_COMPLETED
    if commit:
        db.commit()


def mark_overdue_scheduled_inspections(db: Session) -> int:
    now = datetime.utcnow()
    result = (
        db.query(ScheduledInspection)
        .filter(ScheduledInspection.status == SCHEDULED_PENDING, ScheduledInspection.due_at < now)
        .update({ScheduledInspection.status: SCHEDULED_OVERDUE}, synchronize_session=False)
    )
    db.commit()
    return result or 0


def send_daily_digest_emails(db: Session, *, horizon_days: int = 30) -> int:
    """Send a single digest email per user summarizing pending/overdue inspections."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=horizon_days)
    past_limit = now - timedelta(days=30)
    scheduled_items: list[ScheduledInspection] = (
        db.query(ScheduledInspection)
        .options(selectinload(ScheduledInspection.assignment).selectinload(Assignment.assignee))
        .filter(
            ScheduledInspection.status.in_([SCHEDULED_PENDING, SCHEDULED_OVERDUE]),
            ScheduledInspection.due_at <= horizon,
            ScheduledInspection.due_at >= past_limit,
        )
        .all()
    )

    grouped: dict[str, list[ScheduledInspection]] = defaultdict(list)
    users: dict[str, User] = {}
    for scheduled in scheduled_items:
        assignment = scheduled.assignment
        assignee = assignment.assignee if assignment else None
        if not assignee or not assignee.email:
            continue
        grouped[assignee.id].append(scheduled)
        users[assignee.id] = assignee

    sent = 0
    dashboard_link = build_frontend_url(settings.inspections_dashboard_path)
    for user_id, items in grouped.items():
        user = users.get(user_id)
        if not user:
            continue
        payload = [
            {
                "template_name": scheduled.assignment.template.name if scheduled.assignment and scheduled.assignment.template else "Inspection",
                "location": scheduled.assignment.location if scheduled.assignment else None,
                "due_at": format_datetime(scheduled.due_at),
                "status": scheduled.status,
            }
            for scheduled in sorted(items, key=lambda item: item.due_at or now)
        ]
        if not payload:
            continue
        success = email_service.send_templated_email(
            template_name="daily_digest.html",
            to=user.email,
            subject="Inspection digest – pending & overdue items",
            context={
                "user_name": user.full_name or user.email,
                "inspections": payload,
                "inspection_link": dashboard_link,
            },
        )
        if success:
            sent += 1
    return sent


def send_day_before_due_reminders(db: Session) -> int:
    """Send reminders for inspections due tomorrow (pending only)."""
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    start = datetime.combine(tomorrow, time.min)
    end = datetime.combine(tomorrow, time.max)
    scheduled_items: list[ScheduledInspection] = (
        db.query(ScheduledInspection)
        .options(selectinload(ScheduledInspection.assignment).selectinload(Assignment.assignee))
        .filter(
            ScheduledInspection.status == SCHEDULED_PENDING,
            ScheduledInspection.due_at >= start,
            ScheduledInspection.due_at <= end,
        )
        .all()
    )

    sent = 0
    dashboard_link = build_frontend_url(settings.inspections_dashboard_path)
    for scheduled in scheduled_items:
        assignment = scheduled.assignment
        assignee = assignment.assignee if assignment else None
        if not assignee or not assignee.email:
            continue
        success = email_service.send_templated_email(
            template_name="day_before_due_reminder.html",
            to=assignee.email,
            subject="Reminder: inspection due tomorrow",
            context={
                "user_name": assignee.full_name or assignee.email,
                "template_name": assignment.template.name if assignment and assignment.template else "Inspection",
                "location": assignment.location if assignment else None,
                "due_at": format_datetime(scheduled.due_at),
                "inspection_link": dashboard_link,
            },
        )
        if success:
            sent += 1
    return sent


def _normalize_frequency(value: str | None) -> str:
    if not value:
        return WEEKLY_FREQUENCY
    normalized = value.strip().lower()
    return normalized if normalized in VALID_FREQUENCIES else WEEKLY_FREQUENCY


def _normalize_due_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _next_due_from_seed(
    seed: datetime,
    frequency: str,
    after: datetime,
    end_date: date | None,
) -> datetime | None:
    candidate = seed
    while candidate < after:
        candidate = _advance_due_at(candidate, frequency)
        if end_date and candidate.date() > end_date:
            return None
    if end_date and candidate.date() > end_date:
        return None
    return candidate


def _advance_due_at(current: datetime, frequency: str) -> datetime:
    if frequency == DAILY_FREQUENCY:
        return current + timedelta(days=1)
    if frequency == WEEKLY_FREQUENCY:
        return current + timedelta(weeks=1)
    if frequency == MONTHLY_FREQUENCY:
        year = current.year
        month = current.month + 1
        if month > 12:
            month = 1
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(current.day, last_day)
        return current.replace(year=year, month=month, day=day)
    return current


def _period_start_for_due(due_at: datetime, frequency: str) -> date:
    due_date = due_at.date()
    if frequency == DAILY_FREQUENCY:
        return due_date
    if frequency == WEEKLY_FREQUENCY:
        return _normalize_week_start(due_date)
    if frequency == MONTHLY_FREQUENCY:
        return due_date.replace(day=1)
    return due_date


def _resolve_generation_window(target_week_start: date | None) -> tuple[datetime, datetime]:
    if target_week_start:
        normalized = _normalize_week_start(target_week_start)
        start = datetime.combine(normalized, time.min)
        end = datetime.combine(normalized + timedelta(days=6), time.max)
        return start, end
    now = datetime.utcnow()
    return now, now + timedelta(days=DEFAULT_GENERATION_HORIZON_DAYS)


def _require_admin(user: User) -> None:
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        raise ValueError("Only administrators can manage assignments")


def _normalize_week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _annotate_current_week_completion(db: Session, assignments: list[Assignment]) -> None:
    if not assignments:
        return
    assignment_ids = [assignment.id for assignment in assignments]
    week_start = _normalize_week_start(datetime.utcnow().date())
    window_start = datetime.combine(week_start, time.min)
    window_end = datetime.combine(week_start + timedelta(days=6), time.max)

    scheduled_rows = (
        db.query(ScheduledInspection.assignment_id, ScheduledInspection.status)
        .filter(
            ScheduledInspection.assignment_id.in_(assignment_ids),
            ScheduledInspection.due_at >= window_start,
            ScheduledInspection.due_at <= window_end,
        )
        .all()
    )
    completion_map: dict[int, bool] = defaultdict(bool)
    for assignment_id, status in scheduled_rows:
        if status == SCHEDULED_COMPLETED:
            completion_map[assignment_id] = True

    for assignment in assignments:
        setattr(assignment, "current_week_completed", completion_map.get(assignment.id, False))


def _notify_assignment_created(scheduled: ScheduledInspection) -> None:
    assignment = scheduled.assignment
    assignee = assignment.assignee if assignment else None
    if not assignment or not assignee or not assignee.email:
        return
    email_service.send_templated_email(
        template_name="assignment_created.html",
        to=assignee.email,
        subject="New inspection scheduled",
        context={
            "user_name": assignee.full_name or assignee.email,
            "template_name": assignment.template.name if assignment.template else "Inspection",
            "location": assignment.location,
            "period_start": format_date(scheduled.period_start),
            "due_at": format_datetime(scheduled.due_at),
            "inspection_link": build_frontend_url(settings.inspections_dashboard_path),
        },
    )
