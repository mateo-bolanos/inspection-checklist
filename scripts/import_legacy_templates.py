from __future__ import annotations

"""
Create one legacy checklist template per inspection area found in the
Smartsheet archive, without importing any inspection records.

Templates are named "<Area> Legacy H&S" and mirror the legacy item wording.
Run with:
    python scripts/import_legacy_templates.py
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import ChecklistTemplate
from scripts.import_smartsheet_archive import ensure_template, load_dataframe


def import_templates_only(session: Session) -> dict[str, int]:
    """
    Idempotently create legacy templates, returning counts for reporting.
    """
    _, area_items = load_dataframe()
    stats = {"created": 0, "skipped": 0}

    for area, prompts in area_items.items():
        name = f"{area} Legacy H&S"
        exists = session.query(ChecklistTemplate).filter(ChecklistTemplate.name == name).first()
        ensure_template(session, area, prompts)
        stats["skipped" if exists else "created"] += 1

    session.commit()
    return stats


def main() -> None:
    session = SessionLocal()
    try:
        stats = import_templates_only(session)
    finally:
        session.close()

    print(f"Legacy templates created: {stats['created']}, skipped (already existed): {stats['skipped']}")


if __name__ == "__main__":
    main()
