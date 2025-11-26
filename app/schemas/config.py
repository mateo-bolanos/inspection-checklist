from __future__ import annotations

from pydantic import BaseModel, Field


class SeveritySLARead(BaseModel):
    low_days: int = Field(ge=1)
    medium_days: int = Field(ge=1)
    high_days: int = Field(ge=1)

    class Config:
        from_attributes = True


class SeveritySLAUpdate(BaseModel):
    low_days: int | None = Field(default=None, ge=1)
    medium_days: int | None = Field(default=None, ge=1)
    high_days: int | None = Field(default=None, ge=1)
