from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time
from typing import Any, Mapping

from fpdf import FPDF
from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    ActionStatus,
    CorrectiveAction,
    Inspection,
    InspectionResponse,
    ScheduledInspection,
    TemplateItem,
)


def build_inspection_summary(inspection: Inspection) -> dict:
    return {
        "inspection_id": inspection.id,
        "template": inspection.template.name if inspection.template else None,
        "inspector_id": inspection.inspector_id,
        "status": inspection.status,
        "location": inspection.location,
        "notes": inspection.notes,
        "started_at": inspection.started_at.isoformat() if inspection.started_at else None,
        "submitted_at": inspection.submitted_at.isoformat() if inspection.submitted_at else None,
        "overall_score": inspection.overall_score,
        "responses": [
            {
                "item": response.item.prompt if response.item else None,
                "result": response.result,
                "note": response.note,
                "media": [media.file_url for media in response.media_files],
            }
            for response in inspection.responses
        ],
        "actions": [
            {
                "title": action.title,
                "severity": action.severity,
                "status": action.status,
                "due_date": action.due_date.isoformat() if action.due_date else None,
            }
            for action in inspection.actions
        ],
    }


def _format_datetime(value: str | None) -> str:
    return value or "-"


def _format_optional_number(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_pdf(summary: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Inspection Report", ln=True)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Inspection Info", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, f"Inspection ID: {summary['inspection_id']}", ln=True)
    pdf.cell(0, 6, f"Template: {summary.get('template') or '-'}", ln=True)
    pdf.cell(0, 6, f"Assignee: {summary.get('inspector_id') or '-'}", ln=True)
    pdf.cell(0, 6, f"Location: {summary.get('location') or '-'}", ln=True)
    pdf.cell(0, 6, f"Status: {summary.get('status')}", ln=True)
    pdf.cell(0, 6, f"Started: {_format_datetime(summary.get('started_at'))}", ln=True)
    pdf.cell(0, 6, f"Submitted: {_format_datetime(summary.get('submitted_at'))}", ln=True)
    pdf.cell(0, 6, f"Score: {_format_optional_number(summary.get('overall_score'))}", ln=True)
    if summary.get("notes"):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 6, "Notes", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, summary["notes"])
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Responses", ln=True)
    pdf.set_font("Helvetica", size=11)
    if summary.get("responses"):
        for idx, response in enumerate(summary.get("responses", []), start=1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, f"{idx}. {response.get('item') or 'Template item'}")
            pdf.set_font("Helvetica", size=11)
            pdf.cell(0, 6, f"Result: {response.get('result') or '-'}", ln=True)
            pdf.multi_cell(0, 6, f"Notes: {response.get('note') or 'No notes captured'}")
            if response.get("media"):
                pdf.multi_cell(0, 6, f"Attachments: {', '.join(response['media'])}")
            pdf.ln(1)
    else:
        pdf.cell(0, 6, "No responses recorded.", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Issues & Corrective Actions", ln=True)
    pdf.set_font("Helvetica", size=11)
    if summary.get("actions"):
        for action in summary.get("actions", []):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, f"- {action.get('title')} ({action.get('severity')})")
            pdf.set_font("Helvetica", size=11)
            pdf.cell(
                0,
                6,
                f"Status: {action.get('status')} | Due: {_format_datetime(action.get('due_date'))}",
                ln=True,
            )
            pdf.ln(1)
    else:
        pdf.cell(0, 6, "No issues linked to this inspection.", ln=True)

    return _pdf_bytes(pdf)


def _combine_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)
    return start_dt, end_dt


def _summarize_counter(counter: Mapping[str, int]) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda entry: entry[1], reverse=True)


def build_inspections_range_summary(
    db: Session,
    start_date: date,
    end_date: date,
    filters: Mapping[str, Any] | None = None,
    *,
    limit_failures: int = 5,
) -> bytes:
    """
    Build an aggregate snapshot for inspections submitted within the supplied date range.

    The range uses Inspection.submitted_at to ensure only submitted inspections are included.
    """

    filters = filters or {}
    start_dt, end_dt = _combine_range(start_date, end_date)
    base_query = (
        db.query(Inspection)
        .options(selectinload(Inspection.template), selectinload(Inspection.inspector))
        .filter(
            Inspection.submitted_at.isnot(None),
            Inspection.submitted_at >= start_dt,
            Inspection.submitted_at <= end_dt,
        )
    )

    assignee_id = filters.get("assignee_id")
    if assignee_id:
        base_query = base_query.filter(Inspection.inspector_id == assignee_id)

    template_filter = filters.get("template_id")
    if template_filter:
        base_query = base_query.filter(Inspection.template_id == template_filter)

    location_filter_label: str | None = None
    raw_location_id = filters.get("location_id")
    location_name = filters.get("location")
    location_id: int | None = None
    if raw_location_id not in (None, "", 0):
        try:
            location_id = int(raw_location_id)
        except (TypeError, ValueError):
            location_id = None
    if location_id:
        base_query = base_query.filter(Inspection.location_id == location_id)
        location_filter_label = f"Location ID {location_id}"
    elif location_name:
        base_query = base_query.filter(Inspection.location == location_name)
        location_filter_label = location_name

    inspections = base_query.order_by(Inspection.submitted_at.asc()).all()
    inspection_ids = [inspection.id for inspection in inspections]

    status_counts = Counter(inspection.status for inspection in inspections)
    template_counts = Counter(
        (inspection.template.name if inspection.template else "Unspecified template")
        for inspection in inspections
    )
    location_counts = Counter((inspection.location or "Unspecified location") for inspection in inspections)

    scheduled_totals = {"scheduled": 0, "completed": 0}
    if inspections:
        scheduled_totals["scheduled"] = (
            db.query(func.count(ScheduledInspection.id))
            .filter(ScheduledInspection.due_at >= start_dt, ScheduledInspection.due_at <= end_dt)
            .scalar()
            or 0
        )
        scheduled_totals["completed"] = (
            db.query(func.count(Inspection.id))
            .join(ScheduledInspection, Inspection.scheduled_inspection_id == ScheduledInspection.id)
            .filter(Inspection.id.in_(inspection_ids))
            .scalar()
            or 0
        )

    open_actions_by_severity: dict[str, int] = {}
    overdue_actions_by_severity: dict[str, int] = {}
    now = datetime.utcnow()
    if inspection_ids:
        open_rows = (
            db.query(CorrectiveAction.severity, func.count(CorrectiveAction.id))
            .filter(
                CorrectiveAction.inspection_id.in_(inspection_ids),
                CorrectiveAction.status != ActionStatus.closed.value,
            )
            .group_by(CorrectiveAction.severity)
            .all()
        )
        for severity, count in open_rows:
            open_actions_by_severity[severity] = count

        overdue_rows = (
            db.query(CorrectiveAction.severity, func.count(CorrectiveAction.id))
            .filter(
                CorrectiveAction.inspection_id.in_(inspection_ids),
                CorrectiveAction.status != ActionStatus.closed.value,
                CorrectiveAction.due_date.isnot(None),
                CorrectiveAction.due_date < now,
            )
            .group_by(CorrectiveAction.severity)
            .all()
        )
        for severity, count in overdue_rows:
            overdue_actions_by_severity[severity] = count

    top_failures: list[dict[str, Any]] = []
    if inspection_ids:
        failure_rows = (
            db.query(
                TemplateItem.prompt,
                func.count(InspectionResponse.id).label("total"),
                func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).label("failures"),
            )
            .join(TemplateItem, TemplateItem.id == InspectionResponse.template_item_id)
            .join(Inspection, Inspection.id == InspectionResponse.inspection_id)
            .filter(Inspection.id.in_(inspection_ids))
            .group_by(TemplateItem.id, TemplateItem.prompt)
            .order_by(func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).desc())
            .limit(limit_failures)
            .all()
        )
        for prompt, total, failures in failure_rows:
            if not failures:
                continue
            failure_rate = round((failures / total) * 100, 2) if total else 0.0
            top_failures.append({"prompt": prompt, "failures": failures, "fail_rate": failure_rate})

    filters_summary = {
        "Date range": f"{start_date.isoformat()} - {end_date.isoformat()}",
    }
    if assignee_id:
        filters_summary["Assignee"] = assignee_id
    if template_filter:
        filters_summary["Template"] = template_filter
    if location_filter_label:
        filters_summary["Location"] = location_filter_label

    return {
        "inspections": inspections,
        "status_counts": status_counts,
        "template_counts": template_counts,
        "location_counts": location_counts,
        "scheduled_totals": scheduled_totals,
        "open_actions_by_severity": open_actions_by_severity,
        "overdue_actions_by_severity": overdue_actions_by_severity,
        "top_failures": top_failures,
        "filters": filters_summary,
    }


def generate_inspections_range_pdf(
    db: Session,
    start_date: date,
    end_date: date,
    filters: Mapping[str, Any] | None = None,
    *,
    limit_failures: int = 5,
) -> bytes:
    """
    Build a consolidated PDF for inspections submitted within the supplied range.

    The range uses Inspection.submitted_at, ensuring that only submitted inspections are considered.
    """

    summary = build_inspections_range_summary(
        db,
        start_date,
        end_date,
        filters,
        limit_failures=limit_failures,
    )
    inspections = summary["inspections"]
    status_counts = summary["status_counts"]
    template_counts = summary["template_counts"]
    location_counts = summary["location_counts"]
    scheduled_totals = summary["scheduled_totals"]
    open_actions_by_severity = summary["open_actions_by_severity"]
    overdue_actions_by_severity = summary["overdue_actions_by_severity"]
    top_failures = summary["top_failures"]
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Inspection Summary Report", ln=True)
    pdf.set_font("Helvetica", size=11)
    for label, value in summary["filters"].items():
        pdf.cell(0, 6, f"{label}: {value}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, f"Total inspections: {len(inspections)}", ln=True)
    if status_counts:
        for status, count in _summarize_counter(status_counts):
            readable = status.replace("_", " ").title()
            pdf.cell(0, 6, f"- {readable}: {count}", ln=True)
    else:
        pdf.cell(0, 6, "No inspections found for this range.", ln=True)

    if scheduled_totals["scheduled"]:
        completed = scheduled_totals["completed"]
        scheduled_total = scheduled_totals["scheduled"]
        pdf.cell(
            0,
            6,
            f"Scheduled completion: {completed}/{scheduled_total} ({(completed / scheduled_total) * 100:.1f}%)",
            ln=True,
        )
    pdf.ln(3)

    def _render_breakdown(title: str, data: Mapping[str, int]) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", size=11)
        if not data:
            pdf.cell(0, 6, "No data.", ln=True)
            pdf.ln(2)
            return
        for label, count in _summarize_counter(data):
            pdf.cell(0, 6, f"- {label}: {count}", ln=True)
        pdf.ln(2)

    _render_breakdown("By Template", template_counts)
    _render_breakdown("By Location", location_counts)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Issues Overview", ln=True)
    pdf.set_font("Helvetica", size=11)
    if open_actions_by_severity:
        pdf.cell(0, 6, "Open issues:", ln=True)
        for severity, count in _summarize_counter(open_actions_by_severity):
            pdf.cell(0, 6, f"  - {severity.title()}: {count}", ln=True)
    else:
        pdf.cell(0, 6, "No open issues for this selection.", ln=True)
    if overdue_actions_by_severity:
        pdf.cell(0, 6, "Overdue issues:", ln=True)
        for severity, count in _summarize_counter(overdue_actions_by_severity):
            pdf.cell(0, 6, f"  - {severity.title()}: {count}", ln=True)
    pdf.ln(3)

    if top_failures:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Top Failing Items", ln=True)
        pdf.set_font("Helvetica", size=11)
        for item in top_failures:
            pdf.multi_cell(
                0,
                6,
                f"- {item['prompt']} ({item['failures']} fails, {item['fail_rate']:.1f}% of responses)",
            )
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Inspection Details", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    column_defs = [
        ("ID", 12),
        ("Template", 50),
        ("Status", 22),
        ("Location", 40),
        ("Submitted", 40),
    ]
    for header, width in column_defs:
        pdf.cell(width, 7, header, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", size=10)
    if inspections:
        for inspection in inspections:
            pdf.cell(column_defs[0][1], 6, str(inspection.id), border=1)
            pdf.cell(
                column_defs[1][1],
                6,
                _truncate_text(inspection.template.name if inspection.template else "Template"),
                border=1,
            )
            pdf.cell(column_defs[2][1], 6, inspection.status.title(), border=1)
            pdf.cell(
                column_defs[3][1],
                6,
                _truncate_text(inspection.location or "—"),
                border=1,
            )
            submitted = inspection.submitted_at.strftime("%Y-%m-%d %H:%M") if inspection.submitted_at else "-"
            pdf.cell(column_defs[4][1], 6, submitted, border=1)
            pdf.ln()
    else:
        pdf.cell(0, 7, "No inspections to list.", border=1, ln=True)

    return _pdf_bytes(pdf)


def _truncate_text(value: str, max_len: int = 24) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


def _pdf_bytes(pdf: FPDF) -> bytes:
    output = pdf.output(dest="S")
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    return output.encode("latin1")
