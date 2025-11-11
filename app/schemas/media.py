from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.auth import UserRead


class MediaFileRead(BaseModel):
    id: str
    file_url: str
    description: str | None = None
    created_at: datetime
    action_id: int | None = None
    response_id: str | None = None
    uploaded_by: UserRead | None = None

    class Config:
        from_attributes = True
