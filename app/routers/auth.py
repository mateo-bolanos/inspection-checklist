from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import Token, UserRead
from app.services import auth as auth_service

router = APIRouter()


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_service.issue_token_for_user(user)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def read_me(current_user=Depends(auth_service.get_current_active_user)) -> UserRead:  # type: ignore[assignment]
    return current_user
