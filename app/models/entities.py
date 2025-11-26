from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    admin = "admin"
    inspector = "inspector"
    reviewer = "reviewer"
    action_owner = "action_owner"


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default=UserRole.inspector.value)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="inspector",
        cascade="all, delete",
        foreign_keys="Inspection.inspector_id",
    )
    actions_assigned: Mapped[list["CorrectiveAction"]] = relationship(
        back_populates="assignee",
        cascade="all, delete",
        foreign_keys="CorrectiveAction.assigned_to_id",
    )
    inspections_created: Mapped[list["Inspection"]] = relationship(
        back_populates="created_by",
        cascade="all, delete",
        foreign_keys="Inspection.created_by_id",
    )
    actions_started: Mapped[list["CorrectiveAction"]] = relationship(
        back_populates="started_by",
        cascade="all, delete",
        foreign_keys="CorrectiveAction.started_by_id",
    )
    actions_closed: Mapped[list["CorrectiveAction"]] = relationship(
        back_populates="closed_by",
        cascade="all, delete",
        foreign_keys="CorrectiveAction.closed_by_id",
    )
    uploads: Mapped[list["MediaFile"]] = relationship(
        back_populates="uploaded_by",
        cascade="all, delete",
        foreign_keys="MediaFile.uploaded_by_id",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="assignee",
        cascade="all, delete",
        foreign_keys="Assignment.assigned_to_id",
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assigned_to_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    frequency: Mapped[str] = mapped_column(String, default="weekly", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_due_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    assignee: Mapped[User] = relationship(back_populates="assignments")
    template: Mapped["ChecklistTemplate | None"] = relationship(back_populates="assignments")
    scheduled_inspections: Mapped[list["ScheduledInspection"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )

    @property
    def template_name(self) -> str | None:
        return self.template.name if self.template else None


class ScheduledInspection(Base):
    __tablename__ = "scheduled_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    assignment: Mapped[Assignment] = relationship(back_populates="scheduled_inspections")
    inspection: Mapped["Inspection | None"] = relationship(back_populates="scheduled_inspection", uselist=False)


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sections: Mapped[list["TemplateSection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateSection.order_index"
    )
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="template")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="template")


class TemplateSection(Base):
    __tablename__ = "template_sections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    order_index: Mapped[int] = mapped_column(default=0)

    template: Mapped[ChecklistTemplate] = relationship(back_populates="sections")
    items: Mapped[list["TemplateItem"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="TemplateItem.order_index"
    )


class TemplateItem(Base):
    __tablename__ = "template_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    section_id: Mapped[str] = mapped_column(ForeignKey("template_sections.id", ondelete="CASCADE"))
    prompt: Mapped[str] = mapped_column(Text())
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_evidence_on_fail: Mapped[bool] = mapped_column(
        "requires_attachment_on_fail",
        Boolean,
        default=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(default=0)

    section: Mapped[TemplateSection] = relationship(back_populates="items")
    responses: Mapped[list["InspectionResponse"]] = relationship(back_populates="item")


class InspectionStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class InspectionOrigin(str, Enum):
    assignment = "assignment"
    independent = "independent"


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    inspections: Mapped[list["Inspection"]] = relationship(back_populates="location_ref")


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    inspector_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    scheduled_inspection_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheduled_inspections.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default=InspectionStatus.draft.value)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inspection_origin: Mapped[str] = mapped_column(
        String,
        default=InspectionOrigin.independent.value,
        nullable=False,
    )

    template: Mapped[ChecklistTemplate] = relationship(back_populates="inspections")
    inspector: Mapped[User] = relationship(
        back_populates="inspections",
        foreign_keys=[inspector_id],
    )
    created_by: Mapped[User] = relationship(
        back_populates="inspections_created",
        foreign_keys=[created_by_id],
    )
    location_ref: Mapped[Location | None] = relationship(back_populates="inspections")
    scheduled_inspection: Mapped[ScheduledInspection | None] = relationship(back_populates="inspection")
    responses: Mapped[list["InspectionResponse"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    note_entries: Mapped[list["InspectionNote"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="InspectionNote.created_at",
    )


class InspectionResponse(Base):
    __tablename__ = "inspection_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"))
    template_item_id: Mapped[str] = mapped_column(ForeignKey("template_items.id"))
    result: Mapped[str] = mapped_column(String, default="pending")
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="responses")
    item: Mapped[TemplateItem] = relationship(back_populates="responses")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="response", cascade="all, delete-orphan")
    actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="response")
    note_entries: Mapped[list["InspectionResponseNote"]] = relationship(
        back_populates="response",
        cascade="all, delete-orphan",
        order_by="InspectionResponseNote.created_at",
    )

    @property
    def media_urls(self) -> list[str]:
        return [media.file_url for media in self.media_files]


class ActionSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ActionStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    response_id: Mapped[str | None] = mapped_column(ForeignKey("inspection_responses.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    severity: Mapped[str] = mapped_column(String, default=ActionSeverity.medium.value)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default=ActionStatus.open.value)
    started_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    closed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="actions")
    response: Mapped[InspectionResponse | None] = relationship(back_populates="actions")
    assignee: Mapped[User | None] = relationship(
        back_populates="actions_assigned",
        foreign_keys=[assigned_to_id],
    )
    started_by: Mapped[User] = relationship(
        back_populates="actions_started",
        foreign_keys=[started_by_id],
    )
    closed_by: Mapped[User | None] = relationship(
        back_populates="actions_closed",
        foreign_keys=[closed_by_id],
    )
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="action", cascade="all, delete-orphan")
    note_entries: Mapped[list["CorrectiveActionNote"]] = relationship(
        back_populates="action",
        cascade="all, delete-orphan",
        order_by="CorrectiveActionNote.created_at",
    )

    @property
    def media_urls(self) -> list[str]:
        return [media.file_url for media in self.media_files]


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    response_id: Mapped[str | None] = mapped_column(ForeignKey("inspection_responses.id", ondelete="CASCADE"))
    action_id: Mapped[int | None] = mapped_column(ForeignKey("corrective_actions.id", ondelete="CASCADE"))
    file_url: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    response: Mapped[InspectionResponse | None] = relationship(back_populates="media_files")
    action: Mapped[CorrectiveAction | None] = relationship(back_populates="media_files")
    uploaded_by: Mapped[User | None] = relationship(
        back_populates="uploads",
        foreign_keys=[uploaded_by_id],
    )


class InspectionNote(Base):
    __tablename__ = "inspection_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inspection: Mapped[Inspection] = relationship(back_populates="note_entries")
    author: Mapped[User] = relationship()


class InspectionResponseNote(Base):
    __tablename__ = "inspection_response_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    response_id: Mapped[str] = mapped_column(ForeignKey("inspection_responses.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    response: Mapped[InspectionResponse] = relationship(back_populates="note_entries")
    author: Mapped[User] = relationship()


class CorrectiveActionNote(Base):
    __tablename__ = "action_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    action: Mapped["CorrectiveAction"] = relationship(back_populates="note_entries")
    author: Mapped[User] = relationship()


class SeveritySLA(Base):
    """
    Stores the configurable SLA (in days) per severity.
    There should only be a single row in this table.
    """

    __tablename__ = "severity_sla"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, default=1)
    low_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    medium_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    high_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
