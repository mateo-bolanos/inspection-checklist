from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    ActionSeverity,
    ActionStatus,
    CorrectiveAction,
    CorrectiveActionNote,
    Inspection,
    InspectionResponse,
    MediaFile,
    User,
    UserRole,
)
from app.schemas.action import CorrectiveActionCreate, CorrectiveActionUpdate
from app.services import config as config_service
from app.services import email as email_service
from app.services import note_history as note_history_service

logger = logging.getLogger(__name__)

VALID_STATUSES = {status.value for status in ActionStatus}
RISK_LEVELS = {ActionSeverity.low.value, ActionSeverity.medium.value, ActionSeverity.high.value}


def _apply_resolution_notes(db: Session, action: CorrectiveAction, user_id: str, value: str | None) -> None:
    previous_value = (action.resolution_notes or "").strip()
    action.resolution_notes = value
    next_value = (value or "").strip()
    if next_value and next_value != previous_value:
        note_history_service.add_action_note(db, action.id, user_id, value)


def get_due_date_for_severity(db: Session, created_at: datetime, severity: str) -> datetime:
    """Translate severity into a due date using the configurable SLA settings."""
    sla = config_service.get_severity_sla(db)
    mapping = {
        ActionSeverity.low.value: sla.low_days,
        ActionSeverity.medium.value: sla.medium_days,
        ActionSeverity.high.value: sla.high_days,
    }
    days = mapping.get(severity, sla.medium_days)
    return created_at + timedelta(days=days)


def _normalize_severity(value: str | None, default: str) -> str:
    if not value:
        return default
    lowered = value.strip().lower()
    return lowered if lowered in RISK_LEVELS else default


def _derive_risk_level(occurrence: str | None, injury: str | None, fallback: str) -> str:
    """Average the two severity inputs instead of taking the max (low+high => medium)."""
    occ = _normalize_severity(occurrence, None)
    inj = _normalize_severity(injury, None)
    if not occ and not inj:
        return _normalize_severity(None, fallback)

    def _score(value: str | None) -> int:
        if value == ActionSeverity.high.value:
            return 3
        if value == ActionSeverity.medium.value:
            return 2
        if value == ActionSeverity.low.value:
            return 1
        return 0

    scores = [score for score in (_score(occ), _score(inj)) if score > 0]
    if not scores:
        return _normalize_severity(None, fallback)
    avg = sum(scores) / len(scores)
    if avg >= 2.5:
        return ActionSeverity.high.value
    if avg >= 1.5:
        return ActionSeverity.medium.value
    return ActionSeverity.low.value


def list_actions(
    db: Session,
    user: User,
    *,
    assigned_to: str | None = None,
    status: str | None = None,
    location: str | None = None,
) -> list[CorrectiveAction]:
    query = (
        db.query(CorrectiveAction)
        .options(
            selectinload(CorrectiveAction.assignee),
            selectinload(CorrectiveAction.response),
            selectinload(CorrectiveAction.inspection),
            selectinload(CorrectiveAction.started_by),
            selectinload(CorrectiveAction.closed_by),
            selectinload(CorrectiveAction.media_files),
            selectinload(CorrectiveAction.note_entries).selectinload(CorrectiveActionNote.author),
        )
        .order_by(CorrectiveAction.created_at.desc())
    )
    if status:
        if status not in VALID_STATUSES:
            raise ValueError("Invalid status filter")
        query = query.filter(CorrectiveAction.status == status)
    if assigned_to:
        query = query.filter(CorrectiveAction.assigned_to_id == assigned_to)
    if location:
        query = query.join(Inspection).filter(Inspection.location.ilike(f"%{location}%"))

    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    if user.role in privileged_roles:
        return query.all()

    query = query.join(Inspection).filter(
        or_(CorrectiveAction.assigned_to_id == user.id, Inspection.inspector_id == user.id)
    )
    return query.all()


def get_action(db: Session, action_id: int, user: User) -> CorrectiveAction | None:
    query = (
        db.query(CorrectiveAction)
        .options(
            selectinload(CorrectiveAction.assignee),
            selectinload(CorrectiveAction.response),
            selectinload(CorrectiveAction.inspection),
            selectinload(CorrectiveAction.started_by),
            selectinload(CorrectiveAction.closed_by),
            selectinload(CorrectiveAction.media_files),
            selectinload(CorrectiveAction.note_entries).selectinload(CorrectiveActionNote.author),
        )
        .filter(CorrectiveAction.id == action_id)
    )
    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    if user.role in privileged_roles:
        return query.first()

    query = query.join(Inspection).filter(
        or_(CorrectiveAction.assigned_to_id == user.id, Inspection.inspector_id == user.id)
    )
    return query.first()


def list_open_actions_for_item(db: Session, user: User, template_item_id: str) -> list[CorrectiveAction]:
    query = (
        db.query(CorrectiveAction)
        .join(InspectionResponse, CorrectiveAction.response_id == InspectionResponse.id)
        .join(Inspection, Inspection.id == CorrectiveAction.inspection_id)
        .options(
            selectinload(CorrectiveAction.assignee),
            selectinload(CorrectiveAction.response),
            selectinload(CorrectiveAction.inspection),
        )
        .filter(
            InspectionResponse.template_item_id == template_item_id,
            CorrectiveAction.status != ActionStatus.closed.value,
        )
        .order_by(CorrectiveAction.due_date.asc().nullslast())
    )
    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    if user.role in privileged_roles:
        return query.all()
    return query.filter(
        or_(CorrectiveAction.assigned_to_id == user.id, Inspection.inspector_id == user.id)
    ).all()


def create_action(db: Session, user: User, payload: CorrectiveActionCreate) -> CorrectiveAction:
    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    if user.role == UserRole.action_owner.value:
        raise ValueError("Action owners cannot create corrective actions")

    inspection = db.query(Inspection).filter(Inspection.id == payload.inspection_id).first()
    if not inspection:
        raise ValueError("Inspection not found")
    if user.role not in privileged_roles and inspection.inspector_id != user.id:
        raise ValueError("Not allowed to create action for this inspection")

    response = None
    if payload.response_id:
        response = db.query(InspectionResponse).filter(InspectionResponse.id == payload.response_id).first()
        if not response or response.inspection_id != inspection.id:
            raise ValueError("Response not found on inspection")

    if not payload.occurrence_severity or not payload.injury_severity:
        raise ValueError("Provide both occurrence and injury severities for the action")
    assigned_to_id = payload.assigned_to_id or None
    if user.role not in privileged_roles:
        assigned_to_id = None
    elif assigned_to_id:
        assignee = db.query(User).filter(User.id == assigned_to_id, User.is_active.is_(True)).first()
        if not assignee:
            raise ValueError("Assigned user not found")

    status = payload.status or ActionStatus.open.value
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status for action")
    if status == ActionStatus.closed.value:
        raise ValueError("Actions cannot be created already closed")
    severity = _derive_risk_level(payload.occurrence_severity, payload.injury_severity, ActionSeverity.medium.value)
    normalized_occurrence = _normalize_severity(payload.occurrence_severity, None)
    normalized_injury = _normalize_severity(payload.injury_severity, None)
    now = datetime.utcnow()
    due_date = payload.due_date or get_due_date_for_severity(db, now, severity)

    action = CorrectiveAction(
        inspection_id=inspection.id,
        response_id=response.id if response else None,
        title=payload.title,
        description=payload.description,
        severity=severity,
        occurrence_severity=normalized_occurrence,
        injury_severity=normalized_injury,
        due_date=due_date,
        assigned_to_id=assigned_to_id,
        status=status,
        started_by_id=user.id,
        work_order_required=bool(payload.work_order_required),
        work_order_number=payload.work_order_number,
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    _notify_action_assignee(action, db)
    return action


def update_action(db: Session, action: CorrectiveAction, payload: CorrectiveActionUpdate, user: User) -> CorrectiveAction:
    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    is_privileged = user.role in privileged_roles
    is_assignee = action.assigned_to_id == user.id
    inspector_is_owner = bool(action.inspection and action.inspection.inspector_id == user.id)
    if not is_privileged:
        if not is_assignee and not inspector_is_owner:
            raise ValueError("Not allowed to update this action")
        forbidden_fields = [
            payload.title,
            payload.description,
            payload.severity,
            payload.due_date,
            payload.assigned_to_id,
            payload.occurrence_severity,
            payload.injury_severity,
            payload.work_order_number,
            payload.work_order_required,
        ]
        if any(value is not None for value in forbidden_fields):
            raise ValueError("Only managers can change action details or assignment")
        if payload.status == ActionStatus.closed.value:
            raise ValueError("Only managers can close actions")

    if payload.title is not None:
        action.title = payload.title
    if payload.description is not None:
        action.description = payload.description
    if payload.occurrence_severity is not None:
        action.occurrence_severity = _normalize_severity(payload.occurrence_severity, action.occurrence_severity)
    if payload.injury_severity is not None:
        action.injury_severity = _normalize_severity(payload.injury_severity, action.injury_severity)
    if payload.severity is not None:
        action.severity = _normalize_severity(payload.severity, action.severity)
    elif payload.occurrence_severity is not None or payload.injury_severity is not None:
        action.severity = _derive_risk_level(
            payload.occurrence_severity or action.occurrence_severity,
            payload.injury_severity or action.injury_severity,
            action.severity or ActionSeverity.medium.value,
        )
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.assigned_to_id is not None:
        assigned_to_id = payload.assigned_to_id or None
        if assigned_to_id:
            assignee = db.query(User).filter(User.id == assigned_to_id, User.is_active.is_(True)).first()
            if not assignee:
                raise ValueError("Assigned user not found")
        action.assigned_to_id = assigned_to_id
    if payload.work_order_required is not None:
        action.work_order_required = bool(payload.work_order_required)
    if payload.work_order_number is not None:
        action.work_order_number = payload.work_order_number
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise ValueError("Invalid status for action")
        current_status = action.status
        closing = payload.status == ActionStatus.closed.value and current_status != ActionStatus.closed.value
        reopening = payload.status != ActionStatus.closed.value and current_status == ActionStatus.closed.value
        if closing and not is_privileged:
            raise ValueError("Only managers can close actions")
        action.status = payload.status
        if closing:
            notes = payload.resolution_notes or action.resolution_notes
            if action.work_order_required and not (payload.work_order_number or action.work_order_number):
                raise ValueError("Work order number required before closing this action")
            if not notes:
                raise ValueError("Resolution notes are required to close an action")
            _apply_resolution_notes(db, action, user.id, notes)
            action.closed_at = datetime.utcnow()
            action.closed_by_id = user.id
        elif reopening:
            action.closed_at = None
            action.closed_by_id = None
            if payload.resolution_notes is not None:
                _apply_resolution_notes(db, action, user.id, payload.resolution_notes)
            else:
                action.resolution_notes = None
        elif payload.resolution_notes is not None:
            _apply_resolution_notes(db, action, user.id, payload.resolution_notes)
    elif payload.resolution_notes is not None:
        _apply_resolution_notes(db, action, user.id, payload.resolution_notes)

    db.commit()
    db.refresh(action)
    return action


def count_overdue_actions(db: Session) -> int:
    now = datetime.now(timezone.utc)
    return (
        db.query(func.count(CorrectiveAction.id))
        .filter(
            CorrectiveAction.status != ActionStatus.closed.value,
            CorrectiveAction.due_date.isnot(None),
            CorrectiveAction.due_date < now,
        )
        .scalar()
        or 0
    )


def _ensure_action_has_evidence(db: Session, action_id: int) -> None:
    attachments = (
        db.query(func.count(MediaFile.id))
        .filter(MediaFile.action_id == action_id)
        .scalar()
        or 0
    )
    if attachments == 0:
        raise ValueError("Add at least one image attachment before closing an action")


def _notify_action_assignee(action: CorrectiveAction, db: Session) -> None:
    if not action.assigned_to_id:
        return
    assignee = db.query(User).filter(User.id == action.assigned_to_id).first()
    if not assignee or not assignee.email:
        return
    context = {
        "assignee_name": assignee.full_name or assignee.email,
        "action_id": action.id,
        "action_title": action.title,
        "severity": action.severity,
        "due_date": action.due_date,
        "inspection_id": action.inspection_id,
    }
    try:
        email_service.send_templated_email(
            template_name="action_assigned.html",
            to=assignee.email,
            subject=f"New corrective action #{action.id}",
            context=context,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send action assignment email for %s", action.id)
