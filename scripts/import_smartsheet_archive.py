from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
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
    ActionSeverity,
    ActionStatus,
    ChecklistTemplate,
    CorrectiveAction,
    Inspection,
    InspectionOrigin,
    InspectionResponse,
    InspectionStatus,
    TemplateItem,
    TemplateSection,
    User,
    UserRole,
)

EXCEL_PATH = BASE_DIR / "docs" / "Inspection Grid Archive.xlsx"
DEFAULT_PASSWORD = "imported-change-me"

RISK_TO_SEVERITY = {
    "High Risk": ActionSeverity.high.value,
    "Medium Risk": ActionSeverity.medium.value,
    "Low Risk": ActionSeverity.low.value,
}
COLOR_TO_SEVERITY = {
    "Red": ActionSeverity.high.value,
    "Yellow": ActionSeverity.medium.value,
    "Green": ActionSeverity.low.value,
}


def _result_for_row(row: pd.Series) -> str:
    if pd.notna(row.get("Rating Poor")) and float(row.get("Rating Poor", 0)) > 0:
        return "fail"
    if pd.notna(row.get("Rating Good")) and float(row.get("Rating Good", 0)) > 0:
        return "pass"
    return "pending"


def _note_for_row(row: pd.Series) -> str | None:
    bits: list[str] = []
    if pd.notna(row.get("Issue Location/Area")):
        bits.append(f"Location/Area: {row['Issue Location/Area']}")
    if pd.notna(row.get("Issue")):
        bits.append(str(row["Issue"]))
    if pd.notna(row.get("Status")) and str(row["Status"]).strip():
        bits.append(f"Legacy status: {row['Status']}")
    return "\n".join(bits) if bits else None


def _parse_datetime(value: Any) -> datetime | None:
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None


def _severity_for_row(row: pd.Series) -> str:
    risk = row.get("Risk Level")
    if pd.notna(risk) and str(risk) in RISK_TO_SEVERITY:
        return RISK_TO_SEVERITY[str(risk)]
    color = row.get("Severity of Occurrence")
    if pd.notna(color) and str(color) in COLOR_TO_SEVERITY:
        return COLOR_TO_SEVERITY[str(color)]
    likelihood = row.get("Likelihood of Occurring")
    if pd.notna(likelihood) and str(likelihood) in COLOR_TO_SEVERITY:
        return COLOR_TO_SEVERITY[str(likelihood)]
    return ActionSeverity.medium.value


def _action_for_row(row: pd.Series) -> dict[str, Any] | None:
    has_action = pd.notna(row.get("Corrective Action")) and str(row["Corrective Action"]).strip()
    has_issue = pd.notna(row.get("Issue")) and str(row["Issue"]).strip()
    needs_action = _result_for_row(row) == "fail"
    if not (has_action or has_issue or needs_action):
        return None

    title_source = str(row.get("Corrective Action") or "").strip() or str(row.get("Issue") or "").strip()
    title = title_source or f"Issue: {row.get('Inspection Item..')}"
    description_parts: list[str] = []
    if pd.notna(row.get("Issue Location/Area")):
        description_parts.append(f"Location/Area: {row['Issue Location/Area']}")
    if has_issue:
        description_parts.append(str(row["Issue"]))
    if has_action:
        description_parts.append(f"Legacy corrective action: {row['Corrective Action']}")
    if pd.notna(row.get("Responsible to Complete")):
        description_parts.append(f"Responsible: {row['Responsible to Complete']}")
    if pd.notna(row.get("Risk Level")):
        description_parts.append(f"Risk Level: {row['Risk Level']}")
    if pd.notna(row.get("Severity of Occurrence")):
        description_parts.append(f"Severity of Occurrence: {row['Severity of Occurrence']}")
    if pd.notna(row.get("Likelihood of Occurring")):
        description_parts.append(f"Likelihood of Occurring: {row['Likelihood of Occurring']}")

    status_raw = str(row.get("Status") or "").lower()
    close_date = _parse_datetime(row.get("Close Date"))
    status = ActionStatus.closed.value if "complete" in status_raw or close_date else ActionStatus.open.value

    return {
        "title": title,
        "description": "\n".join(description_parts) if description_parts else None,
        "severity": _severity_for_row(row),
        "due_date": _parse_datetime(row.get("Assigned Due Date")) or _parse_datetime(row.get("Default Due Date")),
        "status": status,
        "closed_at": close_date,
        "work_order_required": bool(row.get("Maintenance Work Order Required") == 1),
        "work_order_number": row.get("Maintenance W.O.#") if pd.notna(row.get("Maintenance W.O.#")) else None,
    }


def load_dataframe() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    df = pd.read_excel(EXCEL_PATH, sheet_name="Inspection Grid Archive")
    df = df.dropna(subset=["Inspection Item..", "Inspection Area", "Inspected by", "Inspection Date"]).copy()
    df["Created"] = pd.to_datetime(df["Created"])
    df["Inspection Date"] = pd.to_datetime(df["Inspection Date"]).dt.date
    df["result"] = df.apply(_result_for_row, axis=1)
    df["note"] = df.apply(_note_for_row, axis=1)
    df["action_payload"] = df.apply(_action_for_row, axis=1)

    area_items = {
        area: sorted(group["Inspection Item.."].dropna().unique().tolist())
        for area, group in df.groupby("Inspection Area")
    }
    return df, area_items


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


def ensure_template(session: Session, area: str, prompts: list[str]) -> ChecklistTemplate:
    name = f"{area} Legacy H&S"
    template = session.query(ChecklistTemplate).filter(ChecklistTemplate.name == name).first()
    if template:
        return template

    template = ChecklistTemplate(name=name, description="Imported from Smartsheet archive")
    section = TemplateSection(title=f"{area} Checks", order_index=1, template=template)
    for idx, prompt in enumerate(prompts, start=1):
        TemplateItem(
            prompt=prompt,
            order_index=idx,
            is_required=True,
            requires_evidence_on_fail=False,
            section=section,
        )

    session.add(template)
    session.flush()
    return template


def _overall_score(results: list[str]) -> float:
    scored = [r for r in results if r in {"pass", "fail"}]
    if not scored:
        return 0.0
    passed = sum(1 for r in scored if r == "pass")
    return round((passed / len(scored)) * 100, 2)


def import_inspections(session: Session, df: pd.DataFrame, area_items: dict[str, list[str]]) -> dict[str, Any]:
    grouped = df.sort_values("Created").groupby(["Inspection Area", "Inspection Date", "Inspected by"])
    stats: dict[str, Any] = {"created": 0, "per_area": Counter(), "pending_gaps": []}

    for (area, insp_date, inspector_email), group in grouped:
        dedup = group.sort_values("Created").groupby("Inspection Item..").tail(1)
        created_min = dedup["Created"].min()
        created_max = dedup["Created"].max()
        inspector = ensure_user(session, inspector_email)
        template = ensure_template(session, area, area_items[area])

        inspection = Inspection(
            template_id=template.id,
            inspector_id=inspector.id,
            created_by_id=inspector.id,
            status=InspectionStatus.submitted.value,
            inspection_origin=InspectionOrigin.independent.value,
            location=area,
            notes=(
                f"Imported from Smartsheet on {datetime.utcnow().date().isoformat()} "
                f"(area: {area}, legacy date: {insp_date.isoformat()}, inspector: {inspector_email})"
            ),
            started_at=created_min.to_pydatetime() if hasattr(created_min, "to_pydatetime") else datetime.combine(
                insp_date, datetime.min.time()
            ),
            submitted_at=created_max.to_pydatetime() if hasattr(created_max, "to_pydatetime") else None,
        )
        session.add(inspection)
        session.flush()

        prompt_to_row = {row["Inspection Item.."]: row for _, row in dedup.iterrows()}
        results: list[str] = []
        missing_prompts: list[str] = []
        for item in template.sections[0].items:
            row = prompt_to_row.get(item.prompt)
            if row is None:
                response = InspectionResponse(
                    inspection_id=inspection.id,
                    template_item_id=item.id,
                    result="pending",
                    note="Missing from legacy export",
                )
                missing_prompts.append(item.prompt)
            else:
                response = InspectionResponse(
                    inspection_id=inspection.id,
                    template_item_id=item.id,
                    result=row["result"],
                    note=row["note"],
                )
                session.add(response)
                session.flush()
                if row["action_payload"]:
                    payload = row["action_payload"]
                    action = CorrectiveAction(
                        inspection_id=inspection.id,
                        response_id=response.id,
                        title=payload["title"],
                        description=payload["description"],
                        severity=payload["severity"],
                        due_date=payload["due_date"],
                        status=payload["status"],
                        closed_at=payload["closed_at"],
                        started_by_id=inspector.id,
                        closed_by_id=inspector.id if payload["status"] == ActionStatus.closed.value else None,
                        work_order_required=payload["work_order_required"],
                        work_order_number=payload["work_order_number"],
                    )
                    session.add(action)
                results.append(row["result"])
            if response.id is None:
                session.add(response)

        inspection.overall_score = _overall_score(results)
        stats["created"] += 1
        stats["per_area"][area] += 1
        if missing_prompts:
            stats["pending_gaps"].append(
                {
                    "area": area,
                    "inspection_date": insp_date.isoformat(),
                    "inspector": inspector_email,
                    "missing_items": missing_prompts,
                }
            )

    session.commit()
    return stats


def main() -> None:
    df, area_items = load_dataframe()
    session = SessionLocal()
    try:
        stats = import_inspections(session, df, area_items)
    finally:
        session.close()

    print(f"Imported inspections: {stats['created']}")
    for area, count in stats["per_area"].most_common():
        print(f"  {area}: {count}")
    if stats["pending_gaps"]:
        print("\nInspections with missing items (marked as pending):")
        for gap in stats["pending_gaps"]:
            missing = ", ".join(gap["missing_items"])
            print(f"- {gap['area']} on {gap['inspection_date']} by {gap['inspector']}: {missing}")


if __name__ == "__main__":
    main()
