from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User, UserRole
from app.schemas.auth import UserRead
from app.services import auth as auth_service

router = APIRouter()


@router.get("/", response_model=List[UserRead])
def list_users(
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> List[UserRead]:
    query = db.query(User).order_by(User.full_name.asc())
    if role:
        query = query.filter(User.role == role)
    return query.all()


@router.get("/assignees", response_model=List[UserRead])
def list_action_assignees(
    role: str | None = Query(default=None, description="Comma-separated list of roles"),
    db: Session = Depends(get_db),
    current_user=Depends(auth_service.get_current_active_user),
) -> List[UserRead]:
    query = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.full_name.asc())
    )
    roles = _parse_roles(role)
    if roles:
        query = query.filter(User.role.in_(roles))
    return query.all()


def _parse_roles(role_param: str | None) -> list[str]:
    if role_param:
        roles = {value.strip() for value in role_param.split(",") if value.strip()}
        return [value for value in roles]
    return [UserRole.action_owner.value]
