from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

from app.models.entities import Inspection


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


def render_pdf(summary: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Inspection Report", ln=True)

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Inspection ID: {summary['inspection_id']}", ln=True)
    pdf.cell(0, 8, f"Template: {summary.get('template')}", ln=True)
    pdf.cell(0, 8, f"Status: {summary.get('status')}", ln=True)
    pdf.cell(0, 8, f"Score: {summary.get('overall_score')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Responses", ln=True)
    pdf.set_font("Helvetica", size=12)
    for response in summary.get("responses", []):
        pdf.multi_cell(0, 6, f"- {response['item']}: {response['result']} ({response.get('note') or 'No notes'})")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Corrective Actions", ln=True)
    pdf.set_font("Helvetica", size=12)
    for action in summary.get("actions", []):
        pdf.multi_cell(0, 6, f"- {action['title']} [{action['severity']}] - {action['status']}")

    return pdf.output(dest="S").encode("latin1")
