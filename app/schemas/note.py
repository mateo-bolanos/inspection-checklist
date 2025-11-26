from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.auth import UserRead


class NoteEntryRead(BaseModel):
    id: int
    author_id: str
    body: str
    created_at: datetime
    author: UserRead | None = None

    class Config:
        from_attributes = True
