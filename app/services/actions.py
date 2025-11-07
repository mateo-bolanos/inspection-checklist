from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.entities import ActionStatus, CorrectiveAction, Inspection, InspectionResponse, User, UserRole
from app.schemas.action import CorrectiveActionCreate, CorrectiveActionUpdate


def list_actions(db: Session, user: User) -> list[CorrectiveAction]:
    query = (
        db.query(CorrectiveAction)
        .options(selectinload(CorrectiveAction.response), selectinload(CorrectiveAction.inspection))
        .order_by(CorrectiveAction.created_at.desc())
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
    return query.all()


def get_action(db: Session, action_id: str, user: User) -> CorrectiveAction | None:
    query = (
        db.query(CorrectiveAction)
        .options(selectinload(CorrectiveAction.response), selectinload(CorrectiveAction.inspection))
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

    action = CorrectiveAction(
        inspection_id=inspection.id,
        response_id=response.id if response else None,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id,
        status=payload.status,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def update_action(db: Session, action: CorrectiveAction, payload: CorrectiveActionUpdate) -> CorrectiveAction:
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
        action.status = payload.status
        if payload.status == ActionStatus.closed.value:
            action.closed_at = datetime.utcnow()
        else:
            action.closed_at = None
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
