from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.entities import ChecklistTemplate, TemplateItem, TemplateSection, User, UserRole

DEFAULT_USERS = [
    {
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": UserRole.admin.value,
        "password": "adminpass",
    },
    {
        "email": "inspector@example.com",
        "full_name": "Inspector One",
        "role": UserRole.inspector.value,
        "password": "inspectorpass",
    },
    {
        "email": "reviewer@example.com",
        "full_name": "Reviewer Pro",
        "role": UserRole.reviewer.value,
        "password": "reviewerpass",
    },
    {
        "email": "employee@example.com",
        "full_name": "Action Owner",
        "role": UserRole.action_owner.value,
        "password": "employeepass",
    },
]


def _get_or_create_user(db: Session, *, email: str, full_name: str, role: str, password: str) -> None:
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        return

    user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    db.flush()


def _ensure_template(
    db: Session,
    *,
    name: str,
    description: str,
    sections: list[dict[str, Any]],
) -> None:
    """
    Idempotently create a checklist template with ordered sections/items.
    """

    exists = db.query(ChecklistTemplate).filter(ChecklistTemplate.name == name).first()
    if exists:
        return

    template = ChecklistTemplate(name=name, description=description)
    for section_index, section_config in enumerate(sections, start=1):
        section = TemplateSection(
            title=section_config["title"],
            order_index=section_index,
            template=template,
        )
        for item_index, item in enumerate(section_config["items"], start=1):
            TemplateItem(
                prompt=item["prompt"],
                order_index=item_index,
                is_required=item.get("is_required", True),
                requires_evidence_on_fail=item.get("requires_evidence_on_fail", True),
                section=section,
            )

    db.add(template)


def seed_initial_data() -> None:
    db = SessionLocal()
    try:
        for user_config in DEFAULT_USERS:
            _get_or_create_user(db, **user_config)

        _ensure_template(
            db,
            name="Warehouse Safety",
            description="Default template",
            sections=[
                {
                    "title": "General Safety",
                    "items": [
                        {"prompt": "Fire extinguishers accessible"},
                        {"prompt": "Emergency exits clear"},
                        {"prompt": "PPE available"},
                    ],
                }
            ],
        )
        _ensure_template(
            db,
            name="Shipping Safety",
            description="Shipping inspection covering housekeeping, equipment, and PPE expectations.",
            sections=[
                {
                    "title": "Shipping Area Checks",
                    "items": [
                        {
                            "prompt": (
                                "General Housekeeping – What to look for:\n"
                                "- Tidy work area\n"
                                "- Unobstructed floor and walking paths\n"
                                "- Organized tools"
                            )
                        },
                        {
                            "prompt": (
                                "Units and Stock – What to look for:\n"
                                "- Stored in a safe manner\n"
                                "- Stacked units stable\n"
                                "- Stacked so there is no tipping or fall hazard"
                            )
                        },
                        {
                            "prompt": (
                                "Trailers – What to look for:\n"
                                "- Trailers being loaded/unloaded are chocked\n"
                                "- Loads are safely restrained"
                            )
                        },
                        {
                            "prompt": (
                                "Loading Bars – What to look for:\n"
                                "- Loading bars used properly during loading/unloading\n"
                                "- Stored safely when not in use"
                            )
                        },
                        {
                            "prompt": (
                                "Forklift Operation – What to look for:\n"
                                "- Drivers wearing seatbelts\n"
                                "- Safe operation practices\n"
                                "- Blue lights working\n"
                                "- Safe speed of travel\n"
                                "- Yielding to pedestrians\n"
                                "- Aisles clear for safe passage"
                            )
                        },
                        {
                            "prompt": (
                                "Forklift Inspection Records – What to look for:\n"
                                "- Records completed for all forklifts"
                            )
                        },
                        {
                            "prompt": (
                                "Electrical Equipment – What to look for:\n"
                                "- No faults or sparking\n"
                                "- No overheating or excess heat\n"
                                "- Functions properly"
                            )
                        },
                        {
                            "prompt": (
                                "Emergency Equipment – What to look for:\n"
                                "- Fire preparedness\n"
                                "- Fire extinguisher pressure within range\n"
                                "- Exit signage functioning and clear\n"
                                "- Emergency plan posted and legible"
                            )
                        },
                        {
                            "prompt": (
                                "Employee PPE – What to look for:\n"
                                "- Availability of required PPE\n"
                                "- Compliance with PPE use\n"
                                "- Condition of PPE (gloves, bump caps, steel toes)"
                            )
                        },
                        {
                            "prompt": (
                                "MSD Hazards – What to look for:\n"
                                "- Proper labeling of hazardous items\n"
                                "- Work instructions available\n"
                                "- Required signage and procedures posted"
                            )
                        },
                    ],
                }
            ],
        )

        db.commit()
    finally:
        db.close()
