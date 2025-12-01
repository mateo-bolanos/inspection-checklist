from __future__ import annotations

from datetime import datetime, date, time
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.entities import (  # noqa: E402
    ChecklistTemplate,
    Inspection,
    InspectionOrigin,
    InspectionResponse,
    InspectionStatus,
    TemplateItem,
    User,
    UserRole,
)

CSV_PATH = Path("docs/shipping_2025_inspections_wide.csv")
DEFAULT_PASSWORD = "imported-change-me"
LOCATION = "Shipping"
# Target the modern template with guidance prompts.
TEMPLATE_NAME = "Shipping Safety"

ITEMS = [
    "General Housekeeping",
    "Units and Stock",
    "Trailers",
    "Loading Bars",
    "Forklift Operation",
    "Forklift Inspection Records",
    "Electrical Equipment",
    "Emergency Equipment",
    "Employee PPE",
    "MSD Hazards",
]


def ensure_user(session: Session, email: str) -> User:
    user = session.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        full_name=email.split("@")[0],
        role=UserRole.inspector.value,
        hashed_password=get_password_hash(DEFAULT_PASSWORD),
    )
    session.add(user)
    session.flush()
    return user


def _combine_issue_info(row: pd.Series, prefix: str) -> str | None:
    parts: list[str] = []
    loc = row.get(f"{prefix}_issue_location")
    issue = row.get(f"{prefix}_issue")
    action = row.get(f"{prefix}_corrective_action")
    status = row.get(f"{prefix}_status")
    if pd.notna(loc) and str(loc).strip():
        parts.append(f"Location: {loc}")
    if pd.notna(issue) and str(issue).strip():
        parts.append(str(issue))
    if pd.notna(action) and str(action).strip():
        parts.append(f"Legacy corrective action: {action}")
    if pd.notna(status) and str(status).strip():
        parts.append(f"Legacy status: {status}")
    if not parts:
        return None
    return "\n".join(parts)


def _result_value(raw: Any) -> str:
    val = str(raw or "").strip().lower()
    if val in {"pass", "fail", "pending"}:
        return val
    return "pending"


def _overall_score(results: list[str]) -> float:
    scored = [r for r in results if r in {"pass", "fail"}]
    if not scored:
        return 0.0
    passed = sum(1 for r in scored if r == "pass")
    return round((passed / len(scored)) * 100, 2)


def _find_template(session: Session) -> ChecklistTemplate:
    template = session.query(ChecklistTemplate).filter(ChecklistTemplate.name == TEMPLATE_NAME).first()
    if not template:
        raise RuntimeError(f"Template '{TEMPLATE_NAME}' not found. Create it before importing.")
    return template


def _normalize_label(label: str) -> str:
    # Strip guidance suffixes like " – What to look for:"
    return label.split("–")[0].split("-")[0].strip()


def _get_item_lookup(template: ChecklistTemplate) -> dict[str, TemplateItem]:
    lookup = {}
    for item in template.sections[0].items:
        normalized = _normalize_label(item.prompt)
        lookup[normalized] = item
    return lookup


def _existing_inspection(session: Session, template_id: str, inspector_id: str, insp_date: date) -> Inspection | None:
    candidates = (
        session.query(Inspection)
        .filter(Inspection.template_id == template_id, Inspection.inspector_id == inspector_id)
        .all()
    )
    for insp in candidates:
        if insp.started_at and insp.started_at.date() == insp_date:
            return insp
    return None


def import_inspections(session: Session) -> dict[str, int]:
    df = pd.read_csv(CSV_PATH, parse_dates=["started_at", "submitted_at"])
    template = _find_template(session)
    item_lookup = _get_item_lookup(template)

    created = 0
    skipped = 0
    for _, row in df.iterrows():
        insp_date = datetime.fromisoformat(row["inspection_date"]).date()
        inspector_email = row["inspector"]
        inspector = ensure_user(session, inspector_email)

        existing = _existing_inspection(session, template.id, inspector.id, insp_date)
        if existing:
            skipped += 1
            continue

        started_at = row["started_at"].to_pydatetime() if pd.notna(row["started_at"]) else datetime.combine(
            insp_date, time.min
        )
        submitted_at = (
            row["submitted_at"].to_pydatetime()
            if pd.notna(row["submitted_at"])
            else datetime.combine(insp_date, time.max)
        )

        inspection = Inspection(
            template_id=template.id,
            inspector_id=inspector.id,
            created_by_id=inspector.id,
            status=InspectionStatus.submitted.value,
            inspection_origin=InspectionOrigin.independent.value,
            location=LOCATION,
            started_at=started_at,
            submitted_at=submitted_at,
            notes=f"Imported from shipping_2025_inspections_wide.csv (completion flag={row['completion_flag']})",
        )
        session.add(inspection)
        session.flush()

        results: list[str] = []
        for item_name in ITEMS:
            item = item_lookup.get(item_name)
            if not item:
                raise RuntimeError(f"Template missing item '{item_name}' in '{TEMPLATE_NAME}'")
            prefix = item_name.replace(" ", "_").lower()
            result_val = _result_value(row.get(f"{prefix}_result"))
            note_val = _combine_issue_info(row, prefix)
            response = InspectionResponse(
                inspection_id=inspection.id,
                template_item_id=item.id,
                result=result_val,
                note=note_val,
            )
            session.add(response)
            results.append(result_val)

        inspection.overall_score = _overall_score(results)
        created += 1

    session.commit()
    return {"created": created, "skipped": skipped}


def main() -> None:
    session = SessionLocal()
    try:
        stats = import_inspections(session)
    finally:
        session.close()
    print(f"Created inspections: {stats['created']}, skipped (already present): {stats['skipped']}")


if __name__ == "__main__":
    main()
