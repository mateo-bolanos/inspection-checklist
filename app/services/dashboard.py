from __future__ import annotations

from sqlalchemy.orm import Session


def placeholder(db: Session) -> dict[str, str]:
    return {"message": "to be implemented"}
