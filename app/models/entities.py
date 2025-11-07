from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    admin = "admin"
    inspector = "inspector"
    reviewer = "reviewer"


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

    inspections: Mapped[list["Inspection"]] = relationship(back_populates="inspector", cascade="all, delete")
    actions_assigned: Mapped[list["CorrectiveAction"]] = relationship(
        back_populates="assignee",
        cascade="all, delete",
        foreign_keys="CorrectiveAction.assigned_to_id",
    )


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
    order_index: Mapped[int] = mapped_column(default=0)

    section: Mapped[TemplateSection] = relationship(back_populates="items")
    responses: Mapped[list["InspectionResponse"]] = relationship(back_populates="item")


class InspectionStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    inspector_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String, default=InspectionStatus.draft.value)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    template: Mapped[ChecklistTemplate] = relationship(back_populates="inspections")
    inspector: Mapped[User] = relationship(back_populates="inspections")
    responses: Mapped[list["InspectionResponse"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")


class InspectionResponse(Base):
    __tablename__ = "inspection_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"))
    template_item_id: Mapped[str] = mapped_column(ForeignKey("template_items.id"))
    result: Mapped[str] = mapped_column(String, default="pending")
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="responses")
    item: Mapped[TemplateItem] = relationship(back_populates="responses")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="response", cascade="all, delete-orphan")
    actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="response")

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

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    response_id: Mapped[str | None] = mapped_column(ForeignKey("inspection_responses.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    severity: Mapped[str] = mapped_column(String, default=ActionSeverity.medium.value)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default=ActionStatus.open.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="actions")
    response: Mapped[InspectionResponse | None] = relationship(back_populates="actions")
    assignee: Mapped[User | None] = relationship(back_populates="actions_assigned")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="action", cascade="all, delete-orphan")


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    response_id: Mapped[str | None] = mapped_column(ForeignKey("inspection_responses.id", ondelete="CASCADE"))
    action_id: Mapped[str | None] = mapped_column(ForeignKey("corrective_actions.id", ondelete="CASCADE"))
    file_url: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    response: Mapped[InspectionResponse | None] = relationship(back_populates="media_files")
    action: Mapped[CorrectiveAction | None] = relationship(back_populates="media_files")
