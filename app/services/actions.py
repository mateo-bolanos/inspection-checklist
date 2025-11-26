from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
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


def list_actions(
    db: Session,
    user: User,
    *,
    assigned_to: str | None = None,
    status: str | None = None,
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

    privileged_roles = {UserRole.admin.value, UserRole.reviewer.value}
    if user.role in privileged_roles:
        return query.all()

    if user.role == UserRole.action_owner.value:
        query = query.filter(CorrectiveAction.assigned_to_id == user.id)
        return query.all()

    query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
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

    if user.role == UserRole.action_owner.value:
        query = query.filter(CorrectiveAction.assigned_to_id == user.id)
        return query.first()

    query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
    return query.first()


def create_action(db: Session, user: User, payload: CorrectiveActionCreate) -> CorrectiveAction:
    if user.role == UserRole.action_owner.value:
        raise ValueError("Action owners cannot create corrective actions")

    inspection = db.query(Inspection).filter(Inspection.id == payload.inspection_id).first()
    if not inspection:
        raise ValueError("Inspection not found")
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value} and inspection.inspector_id != user.id:
        raise ValueError("Not allowed to create action for this inspection")

    response = None
    if payload.response_id:
        response = db.query(InspectionResponse).filter(InspectionResponse.id == payload.response_id).first()
        if not response or response.inspection_id != inspection.id:
            raise ValueError("Response not found on inspection")

    assigned_to_id = payload.assigned_to_id or None
    if assigned_to_id:
        assignee = db.query(User).filter(User.id == assigned_to_id, User.is_active.is_(True)).first()
        if not assignee:
            raise ValueError("Assigned user not found")

    status = payload.status or ActionStatus.open.value
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status for action")
    if status == ActionStatus.closed.value:
        raise ValueError("Actions cannot be created already closed")
    severity = (payload.severity or ActionSeverity.medium.value).lower()
    now = datetime.utcnow()
    due_date = payload.due_date or get_due_date_for_severity(db, now, severity)

    action = CorrectiveAction(
        inspection_id=inspection.id,
        response_id=response.id if response else None,
        title=payload.title,
        description=payload.description,
        severity=severity,
        due_date=due_date,
        assigned_to_id=assigned_to_id,
        status=status,
        started_by_id=user.id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    _notify_action_assignee(action, db)
    return action


def update_action(db: Session, action: CorrectiveAction, payload: CorrectiveActionUpdate, user: User) -> CorrectiveAction:
    if user.role == UserRole.action_owner.value:
        if action.assigned_to_id != user.id:
            raise ValueError("Not allowed to update this action")
        forbidden_fields = [
            payload.title,
            payload.description,
            payload.severity,
            payload.due_date,
            payload.assigned_to_id,
        ]
        if any(value is not None for value in forbidden_fields):
            raise ValueError("Action owners can only update status and notes")

    if payload.title is not None:
        action.title = payload.title
    if payload.description is not None:
        action.description = payload.description
    if payload.severity is not None:
        action.severity = payload.severity
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.assigned_to_id is not None:
        assigned_to_id = payload.assigned_to_id or None
        if assigned_to_id:
            assignee = db.query(User).filter(User.id == assigned_to_id, User.is_active.is_(True)).first()
            if not assignee:
                raise ValueError("Assigned user not found")
        action.assigned_to_id = assigned_to_id
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise ValueError("Invalid status for action")
        current_status = action.status
        closing = payload.status == ActionStatus.closed.value and current_status != ActionStatus.closed.value
        reopening = payload.status != ActionStatus.closed.value and current_status == ActionStatus.closed.value
        action.status = payload.status
        if closing:
            _ensure_action_has_evidence(db, action.id)
            notes = payload.resolution_notes or action.resolution_notes
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
