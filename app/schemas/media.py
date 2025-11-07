from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MediaFileRead(BaseModel):
    id: str
    file_url: str
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
