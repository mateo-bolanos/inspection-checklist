from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.entities import (
    Assignment,
    ChecklistTemplate,
    CorrectiveAction,
    CorrectiveActionNote,
    Inspection,
    InspectionNote,
    InspectionOrigin,
    InspectionResponse,
    InspectionResponseNote,
    InspectionStatus,
    MediaFile,
    ScheduledInspection,
    TemplateItem,
    TemplateSection,
    User,
    UserRole,
)
from app.schemas.inspection import InspectionCreate, InspectionResponseCreate, InspectionResponseUpdate, InspectionUpdate
from app.services import assignments as assignments_service
from app.services import files as files_service
from app.services import locations as locations_service
from app.services import note_history as note_history_service
from app.services import email as email_service
from app.services.notification_utils import build_frontend_url, format_datetime


def list_inspections(db: Session, user: User) -> list[Inspection]:
    query = (
        db.query(Inspection)
        .options(
            selectinload(Inspection.responses).selectinload(InspectionResponse.item),
            selectinload(Inspection.responses).selectinload(InspectionResponse.media_files),
            selectinload(Inspection.template),
            selectinload(Inspection.created_by),
        )
        .order_by(Inspection.started_at.desc())
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.filter(Inspection.inspector_id == user.id)
    return query.all()


def create_inspection(
    db: Session,
    user: User,
    payload: InspectionCreate,
    *,
    origin: InspectionOrigin = InspectionOrigin.independent,
) -> Inspection:
    template: ChecklistTemplate | None = None
    template_id: str | None = payload.template_id
    resolved_origin = origin
    inspector_id = user.id
    if payload.inspector_id:
        if user.role not in {UserRole.admin.value, UserRole.reviewer.value} and payload.inspector_id != user.id:
            raise ValueError("Not allowed to assign inspector")
        inspector = db.query(User).filter(User.id == payload.inspector_id).first()
        if not inspector:
            raise ValueError("Inspector not found")
        inspector_id = inspector.id
    resolved_location_id, resolved_location_name = _resolve_location_payload(
        db,
        location_id=payload.location_id,
        location_name=payload.location,
    )

    scheduled: ScheduledInspection | None = None
    if payload.scheduled_inspection_id is not None:
        scheduled = (
            db.query(ScheduledInspection)
            .options(
                selectinload(ScheduledInspection.assignment).selectinload(Assignment.template),
            )
            .filter(ScheduledInspection.id == payload.scheduled_inspection_id)
            .first()
        )
        if not scheduled:
            raise ValueError("Scheduled inspection not found")
        if scheduled.status == assignments_service.SCHEDULED_COMPLETED:
            raise ValueError("Scheduled inspection already completed")
        if scheduled.assignment is None:
            raise ValueError("Assignment for scheduled inspection is missing")
        if scheduled.assignment.assigned_to_id != inspector_id:
            raise ValueError("Scheduled inspection belongs to another inspector")
        existing_link = (
            db.query(Inspection.id)
            .filter(Inspection.scheduled_inspection_id == payload.scheduled_inspection_id)
            .first()
        )
        if existing_link:
            raise ValueError("Scheduled inspection already linked to an inspection")
        assignment = scheduled.assignment
        if not assignment.template_id:
            raise ValueError("Assignment is missing a template")
        template = assignment.template
        if template is None:
            template = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == assignment.template_id).first()
        if template is None:
            raise ValueError("Assignment template not found")
        template_id = template.id
        resolved_origin = InspectionOrigin.assignment

    if template is None and template_id is not None:
        template = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == template_id).first()
    if template is None:
        raise ValueError("Template not found")
    inspection = Inspection(
        template_id=template.id,
        inspector_id=inspector_id,
        created_by_id=user.id,
        location=resolved_location_name if resolved_location_name is not None else payload.location,
        location_id=resolved_location_id,
        notes=payload.notes,
        scheduled_inspection_id=payload.scheduled_inspection_id,
        inspection_origin=resolved_origin.value,
    )
    if scheduled is not None:
        # Store the linkage so submission can flip the scheduled slot to completed status later.
        inspection.scheduled_inspection_id = scheduled.id
    db.add(inspection)
    db.flush()
    note_history_service.add_inspection_note(db, inspection.id, user.id, payload.notes)
    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection(db: Session, inspection_id: int, user: User) -> Inspection | None:
    query = (
        db.query(Inspection)
        .options(
            selectinload(Inspection.responses)
            .selectinload(InspectionResponse.item),
            selectinload(Inspection.responses).selectinload(InspectionResponse.media_files),
            selectinload(Inspection.responses)
            .selectinload(InspectionResponse.note_entries)
            .selectinload(InspectionResponseNote.author),
            selectinload(Inspection.actions)
            .selectinload(CorrectiveAction.note_entries)
            .selectinload(CorrectiveActionNote.author),
            selectinload(Inspection.created_by),
            selectinload(Inspection.inspector),
            selectinload(Inspection.template),
            selectinload(Inspection.note_entries).selectinload(InspectionNote.author),
        )
        .filter(Inspection.id == inspection_id)
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.filter(Inspection.inspector_id == user.id)
    return query.first()


def update_inspection(db: Session, inspection: Inspection, payload: InspectionUpdate, user: User) -> Inspection:
    location_field_set = "location_id" in payload.model_fields_set
    location_handled = False

    if location_field_set:
        if payload.location_id is None:
            inspection.location_id = None
            if payload.location is not None:
                inspection.location = payload.location
            location_handled = True
        else:
            resolved_location_id, resolved_location_name = _resolve_location_payload(
                db,
                location_id=payload.location_id,
                location_name=payload.location,
            )
            inspection.location_id = resolved_location_id
            if resolved_location_name is not None:
                inspection.location = resolved_location_name
            location_handled = True

    if not location_handled and payload.location is not None:
        resolved_location_id, resolved_location_name = _resolve_location_payload(
            db,
            location_id=None,
            location_name=payload.location,
        )
        if resolved_location_id is not None:
            inspection.location_id = resolved_location_id
            inspection.location = resolved_location_name
        else:
            inspection.location = payload.location
            inspection.location_id = None
    if payload.notes is not None:
        previous_value = (inspection.notes or "").strip()
        inspection.notes = payload.notes
        next_value = (payload.notes or "").strip()
        if next_value and next_value != previous_value:
            note_history_service.add_inspection_note(db, inspection.id, user.id, payload.notes)
    status_handled = False
    if payload.status is not None:
        status_handled = _set_status(db, inspection, payload.status)
    if not status_handled:
        db.commit()
        db.refresh(inspection)
    return inspection


def submit_inspection(db: Session, inspection: Inspection) -> Inspection:
    _validate_submission_requirements(db, inspection)
    inspection.status = InspectionStatus.submitted.value
    inspection.submitted_at = datetime.utcnow()
    inspection.overall_score = _calculate_overall_score(inspection)
    if inspection.scheduled_inspection_id:
        assignments_service.mark_scheduled_completed(
            db, inspection.scheduled_inspection_id, commit=False
        )
    db.commit()
    db.refresh(inspection)
    return inspection


def approve_inspection(db: Session, inspection: Inspection) -> Inspection:
    if inspection.status != InspectionStatus.submitted.value:
        raise ValueError("Inspection must be submitted before approval")
    inspection.status = InspectionStatus.approved.value
    inspection.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(inspection)
    return inspection


def reject_inspection(db: Session, inspection: Inspection) -> Inspection:
    if inspection.status != InspectionStatus.submitted.value:
        raise ValueError("Inspection must be submitted before rejection")
    inspection.status = InspectionStatus.rejected.value
    inspection.rejected_at = datetime.utcnow()
    db.commit()
    db.refresh(inspection)
    return inspection


def create_response(db: Session, inspection: Inspection, payload: InspectionResponseCreate, user: User) -> InspectionResponse:
    template_item = db.query(TemplateItem).filter(TemplateItem.id == payload.template_item_id).first()
    if not template_item:
        raise ValueError("Template item not found")
    if template_item.section.template_id != inspection.template_id:  # type: ignore[attr-defined]
        raise ValueError("Item does not belong to inspection template")
    existing = (
        db.query(InspectionResponse)
        .filter(
            InspectionResponse.inspection_id == inspection.id,
            InspectionResponse.template_item_id == template_item.id,
        )
        .first()
    )
    if existing:
        raise ValueError("Response already exists for this item")
    response = InspectionResponse(
        inspection_id=inspection.id,
        template_item_id=template_item.id,
        result=payload.result,
        note=payload.note,
    )
    db.add(response)
    db.flush()
    note_history_service.add_response_note(db, response.id, user.id, payload.note)
    _sync_media_files(db, response, payload.media_urls, user.id)
    db.commit()
    db.refresh(response)
    return response


def get_response(db: Session, response_id: str, user: User) -> InspectionResponse | None:
    query = (
        db.query(InspectionResponse)
        .options(
            selectinload(InspectionResponse.media_files),
            selectinload(InspectionResponse.note_entries).selectinload(InspectionResponseNote.author),
        )
        .filter(InspectionResponse.id == response_id)
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.join(Inspection).filter(Inspection.inspector_id == user.id)
    return query.first()


def update_response(
    db: Session, response: InspectionResponse, payload: InspectionResponseUpdate, user: User
) -> InspectionResponse:
    if payload.result is not None:
        response.result = payload.result
    if payload.note is not None:
        previous_value = (response.note or "").strip()
        response.note = payload.note
        next_value = (payload.note or "").strip()
        if next_value and next_value != previous_value:
            note_history_service.add_response_note(db, response.id, user.id, payload.note)
    if payload.media_urls is not None:
        _sync_media_files(db, response, payload.media_urls, user.id)
    db.commit()
    db.refresh(response)
    return response


def _resolve_location_payload(
    db: Session,
    *,
    location_id: int | None,
    location_name: str | None,
    allow_create_from_name: bool = True,
) -> tuple[int | None, str | None]:
    if location_id is not None:
        location = locations_service.get_location_by_id(db, location_id)
        if not location:
            raise ValueError("Location not found")
        return location.id, location.name

    normalized_name = (location_name or "").strip()
    if not normalized_name:
        return None, None

    location = locations_service.ensure_location_by_name(
        db,
        normalized_name,
        create_if_missing=allow_create_from_name,
        auto_commit=False,
    )
    if not location:
        raise ValueError("Location not found")
    return location.id, location.name


def _sync_media_files(db: Session, response: InspectionResponse, urls: list[str] | None, user_id: str | None) -> None:
    if urls is None:
        return
    desired_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url and url not in seen:
            desired_urls.append(url)
            seen.add(url)

    existing_by_url = {media.file_url: media for media in list(response.media_files)}
    desired_set = set(desired_urls)

    # Remove files not in the desired list
    for file_url, media in existing_by_url.items():
        if file_url not in desired_set:
            files_service.delete_media_record(db, media)

    # Add any new URLs
    for url in desired_urls:
        if url in existing_by_url:
            continue
        response.media_files.append(
            MediaFile(file_url=url, uploaded_by_id=user_id, response_id=response.id),
        )

    db.flush()


def _validate_submission_requirements(db: Session, inspection: Inspection) -> None:
    template_items: list[TemplateItem] = (
        db.query(TemplateItem)
        .join(TemplateSection)
        .filter(TemplateSection.template_id == inspection.template_id)
        .all()
    )
    items_by_id = {item.id: item for item in template_items}
    required_item_ids = {item.id for item in template_items if item.is_required}
    responded_ids = {response.template_item_id for response in inspection.responses}
    missing = required_item_ids - responded_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All required items must have responses before submission",
        )

    # Failed responses must carry a corrective action plus at least one attachment (on the response or action).
    def requires_evidence(item: TemplateItem | None) -> bool:
        return True if item is None else bool(item.requires_evidence_on_fail)

    failing_responses = [
        response
        for response in inspection.responses
        if (response.result or "").lower() == "fail"
        and requires_evidence(items_by_id.get(response.template_item_id))
    ]
    if not failing_responses:
        return

    actions_by_response: dict[str, list] = {}
    for action in inspection.actions:
        if action.response_id:
            actions_by_response.setdefault(action.response_id, []).append(action)

    relevant_action_ids = {
        action.id for response in failing_responses for action in actions_by_response.get(response.id, [])
    }
    action_media_counts: dict[int, int] = {}
    if relevant_action_ids:
        action_media_counts = {
            row.action_id: row.attachment_count
            for row in (
                db.query(MediaFile.action_id, func.count(MediaFile.id).label("attachment_count"))
                .filter(MediaFile.action_id.in_(relevant_action_ids))
                .group_by(MediaFile.action_id)
                .all()
            )
        }

    for response in failing_responses:
        item = items_by_id.get(response.template_item_id)
        item_label = (item.prompt if item else response.template_item_id).strip() or "item"
        actions_for_response = actions_by_response.get(response.id, [])
        if not actions_for_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Add a corrective action for failed item '{item_label}' before submitting.",
            )
        response_has_media = len(response.media_files or []) > 0
        action_has_media = any(action_media_counts.get(action.id, 0) > 0 for action in actions_for_response)
        if not (response_has_media or action_has_media):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attach evidence to failed item '{item_label}' or its corrective actions before submitting.",
            )


def _calculate_overall_score(inspection: Inspection) -> float:
    scored_responses: Iterable[InspectionResponse] = [
        resp for resp in inspection.responses if (resp.result or "").lower() in {"pass", "fail"}
    ]
    total = len(scored_responses)
    if total == 0:
        return 0.0
    passed = sum(1 for resp in scored_responses if (resp.result or "").lower() == "pass")
    return round((passed / total) * 100, 2)


def _set_status(db: Session, inspection: Inspection, new_status: str) -> bool:
    if new_status == InspectionStatus.submitted.value:
        submit_inspection(db, inspection)
        return True
    if new_status == InspectionStatus.approved.value:
        approve_inspection(db, inspection)
        return True
    if new_status == InspectionStatus.rejected.value:
        reject_inspection(db, inspection)
        return True
    inspection.status = new_status
    return False


def build_submission_notification_payload(inspection: Inspection) -> dict[str, Any]:
    """Flatten the inspection into a dict so BackgroundTasks can send notifications later."""
    responses = list(inspection.responses or [])
    total_items = len(responses)
    failed_items = sum(1 for resp in responses if (resp.result or "").lower() == "fail")
    inspection_label = _inspection_label(inspection)
    inspection_link = build_frontend_url(
        settings.inspection_view_path_template,
        inspection_id=inspection.id,
    )
    pdf_link = (
        f"{settings.api_public_base_url}/inspections/{inspection.id}/export?format=pdf"
        if settings.api_public_base_url
        else None
    )
    return {
        "base_context": {
            "user_name": "",
            "template_name": inspection_label,
            "location": inspection.location,
            "submitted_at": format_datetime(inspection.submitted_at),
            "total_items": total_items,
            "failed_items": failed_items,
            "inspection_link": inspection_link,
            "pdf_link": pdf_link,
        },
        "inspector_email": inspection.inspector.email if inspection.inspector else None,
        "inspector_name": (inspection.inspector.full_name or inspection.inspector.email)
        if inspection.inspector
        else None,
        "supervisor_email": settings.supervisor_notification_email,
        "supervisor_name": "Supervisor",
    }


def send_submission_notifications(payload: dict[str, Any]) -> None:
    """Send inspection submission summary to inspector and optional supervisor."""
    base_context = payload.get("base_context") or {}
    subject = f"Inspection submitted – {base_context.get('template_name', 'Inspection')}"

    inspector_email = payload.get("inspector_email")
    if inspector_email:
        context = dict(base_context)
        context["user_name"] = payload.get("inspector_name") or inspector_email
        email_service.send_templated_email(
            template_name="inspection_submitted.html",
            to=inspector_email,
            subject=subject,
            context=context,
        )

    supervisor_email = payload.get("supervisor_email")
    if supervisor_email:
        context = dict(base_context)
        context["user_name"] = payload.get("supervisor_name") or "Supervisor"
        email_service.send_templated_email(
            template_name="inspection_submitted.html",
            to=supervisor_email,
            subject=subject,
            context=context,
        )


def _inspection_label(inspection: Inspection) -> str:
    if inspection.template and inspection.template.name:
        return inspection.template.name
    return "Inspection"
