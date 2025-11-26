from __future__ import annotations

from pydantic import BaseModel


class LocationBase(BaseModel):
    name: str


class LocationCreate(LocationBase):
    pass


class LocationRead(LocationBase):
    id: int

    class Config:
        from_attributes = True
