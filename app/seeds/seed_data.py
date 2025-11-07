from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.entities import ChecklistTemplate, TemplateItem, TemplateSection, User, UserRole


def seed_initial_data() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        admin = User(
            email="admin@example.com",
            full_name="Admin User",
            role=UserRole.admin.value,
            hashed_password=get_password_hash("adminpass"),
        )
        inspector = User(
            email="inspector@example.com",
            full_name="Inspector One",
            role=UserRole.inspector.value,
            hashed_password=get_password_hash("inspectorpass"),
        )
        reviewer = User(
            email="reviewer@example.com",
            full_name="Reviewer Pro",
            role=UserRole.reviewer.value,
            hashed_password=get_password_hash("reviewerpass"),
        )
        db.add_all([admin, inspector, reviewer])
        db.flush()

        template = ChecklistTemplate(name="Warehouse Safety", description="Default template")
        section = TemplateSection(title="General Safety", order_index=1, template=template)
        items = [
            TemplateItem(prompt="Fire extinguishers accessible", order_index=1, section=section),
            TemplateItem(prompt="Emergency exits clear", order_index=2, section=section),
            TemplateItem(prompt="PPE available", order_index=3, section=section),
        ]
        db.add_all([template, section, *items])
        db.commit()
    finally:
        db.close()
