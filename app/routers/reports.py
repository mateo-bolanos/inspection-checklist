from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import UserRole
from app.services import auth as auth_service
from app.services import reports as report_service

router = APIRouter()


def _parse_date(value: str | None, label: str) -> date:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required {label} date (expected YYYY-MM-DD)",
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} date '{value}'. Expected YYYY-MM-DD.",
        ) from exc


@router.get("/inspections.pdf")
def export_inspections_report(
    start: str | None = Query(None),
    end: str | None = Query(None),
    assignee_id: str | None = Query(None, alias="assigneeId"),
    template_id: str | None = Query(None, alias="templateId"),
    location_id: str | None = Query(None, alias="locationId"),
    location: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(auth_service.require_role([UserRole.admin.value, UserRole.reviewer.value])),
) -> Response:
    start_date = _parse_date(start, "start")
    end_date = _parse_date(end, "end")
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start date must be on or before end date",
        )

    filters: dict[str, Any] = {}
    if assignee_id:
        filters["assignee_id"] = assignee_id
    if template_id:
        filters["template_id"] = template_id
    if location_id:
        filters["location_id"] = location_id
    elif location:
        filters["location"] = location

    pdf_bytes = report_service.generate_inspections_range_pdf(
        db=db,
        start_date=start_date,
        end_date=end_date,
        filters=filters,
    )
    filename = f"inspections-{start_date.isoformat()}_{end_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
