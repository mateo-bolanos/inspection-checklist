from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    ChecklistTemplate,
    Inspection,
    InspectionResponse,
    InspectionStatus,
    MediaFile,
    TemplateItem,
    TemplateSection,
    User,
    UserRole,
)
from app.schemas.inspection import InspectionCreate, InspectionResponseCreate, InspectionResponseUpdate, InspectionUpdate


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


def create_inspection(db: Session, user: User, payload: InspectionCreate) -> Inspection:
    template = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == payload.template_id).first()
    if not template:
        raise ValueError("Template not found")
    inspector_id = user.id
    if payload.inspector_id:
        if user.role not in {UserRole.admin.value, UserRole.reviewer.value} and payload.inspector_id != user.id:
            raise ValueError("Not allowed to assign inspector")
        inspector = db.query(User).filter(User.id == payload.inspector_id).first()
        if not inspector:
            raise ValueError("Inspector not found")
        inspector_id = inspector.id
    inspection = Inspection(
        template_id=template.id,
        inspector_id=inspector_id,
        created_by_id=user.id,
        location=payload.location,
        notes=payload.notes,
    )
    db.add(inspection)
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
            selectinload(Inspection.actions),
            selectinload(Inspection.created_by),
        )
        .filter(Inspection.id == inspection_id)
    )
    if user.role not in {UserRole.admin.value, UserRole.reviewer.value}:
        query = query.filter(Inspection.inspector_id == user.id)
    return query.first()


def update_inspection(db: Session, inspection: Inspection, payload: InspectionUpdate) -> Inspection:
    if payload.location is not None:
        inspection.location = payload.location
    if payload.notes is not None:
        inspection.notes = payload.notes
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
    _sync_media_files(db, response, payload.media_urls, user.id)
    db.commit()
    db.refresh(response)
    return response


def get_response(db: Session, response_id: str, user: User) -> InspectionResponse | None:
    query = db.query(InspectionResponse).options(selectinload(InspectionResponse.media_files)).filter(
        InspectionResponse.id == response_id
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
        response.note = payload.note
    if payload.media_urls is not None:
        _sync_media_files(db, response, payload.media_urls, user.id)
    db.commit()
    db.refresh(response)
    return response


def _sync_media_files(db: Session, response: InspectionResponse, urls: list[str], user_id: str | None) -> None:
    response.media_files.clear()
    for url in urls:
        response.media_files.append(
            MediaFile(file_url=url, uploaded_by_id=user_id, response_id=response.id),
        )
    db.flush()


def _validate_submission_requirements(db: Session, inspection: Inspection) -> None:
    required_item_ids = {
        item_id
        for (item_id,) in (
            db.query(TemplateItem.id)
            .join(TemplateSection)
            .filter(
                TemplateSection.template_id == inspection.template_id,
                TemplateItem.is_required.is_(True),
            )
        )
    }
    responded_ids = {response.template_item_id for response in inspection.responses}
    missing = required_item_ids - responded_ids
    if missing:
        raise ValueError("All required items must have responses before submission")

    failed_items = [
        response
        for response in inspection.responses
        if (response.result or "").lower() == "fail"
    ]
    for response in failed_items:
        has_action = any(action.response_id == response.id for action in inspection.actions)
        if not has_action:
            raise ValueError("Failed items must have corrective actions before submission")


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
