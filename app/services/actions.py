from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    ActionStatus,
    CorrectiveAction,
    Inspection,
    InspectionResponse,
    MediaFile,
    User,
    UserRole,
)
from app.schemas.action import CorrectiveActionCreate, CorrectiveActionUpdate

VALID_STATUSES = {status.value for status in ActionStatus}


def list_actions(db: Session, user: User) -> list[CorrectiveAction]:
    query = (
        db.query(CorrectiveAction)
        .options(
            selectinload(CorrectiveAction.response),
            selectinload(CorrectiveAction.inspection),
            selectinload(CorrectiveAction.started_by),
            selectinload(CorrectiveAction.closed_by),
        )
        .order_by(CorrectiveAction.created_at.desc())
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
    return query.all()


def get_action(db: Session, action_id: int, user: User) -> CorrectiveAction | None:
    query = (
        db.query(CorrectiveAction)
        .options(
            selectinload(CorrectiveAction.response),
            selectinload(CorrectiveAction.inspection),
            selectinload(CorrectiveAction.started_by),
            selectinload(CorrectiveAction.closed_by),
        )
        .filter(CorrectiveAction.id == action_id)
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
    return query.first()


def create_action(db: Session, user: User, payload: CorrectiveActionCreate) -> CorrectiveAction:
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

    if payload.assigned_to_id:
        assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
        if not assignee:
            raise ValueError("Assigned user not found")

    status = payload.status or ActionStatus.open.value
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status for action")
    if status == ActionStatus.closed.value:
        raise ValueError("Actions cannot be created already closed")

    action = CorrectiveAction(
        inspection_id=inspection.id,
        response_id=response.id if response else None,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id,
        status=status,
        started_by_id=user.id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def update_action(db: Session, action: CorrectiveAction, payload: CorrectiveActionUpdate, user: User) -> CorrectiveAction:
    if payload.title is not None:
        action.title = payload.title
    if payload.description is not None:
        action.description = payload.description
    if payload.severity is not None:
        action.severity = payload.severity
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.assigned_to_id is not None:
        if payload.assigned_to_id:
            assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
            if not assignee:
                raise ValueError("Assigned user not found")
        action.assigned_to_id = payload.assigned_to_id
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
            action.resolution_notes = notes
            action.closed_at = datetime.utcnow()
            action.closed_by_id = user.id
        elif reopening:
            action.closed_at = None
            action.closed_by_id = None
            action.resolution_notes = payload.resolution_notes or None
        elif payload.resolution_notes is not None:
            action.resolution_notes = payload.resolution_notes
    elif payload.resolution_notes is not None:
        action.resolution_notes = payload.resolution_notes

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
