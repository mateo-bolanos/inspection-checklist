from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.entities import (
    ActionSeverity,
    ActionStatus,
    Assignment,
    ChecklistTemplate,
    CorrectiveAction,
    Inspection,
    InspectionOrigin,
    InspectionResponse,
    InspectionStatus,
    Location,
    User,
    UserRole,
)
from app.services import reports as report_service


def authenticate(client: TestClient, username: str, password: str) -> Dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_temp_inspector(email: str, password: str) -> None:
    with SessionLocal() as db:
        if db.query(User).filter(User.email == email).first():
            return
        user = User(
            email=email,
            full_name="Temp Inspector",
            role=UserRole.inspector.value,
            hashed_password=get_password_hash(password),
        )
        db.add(user)
        db.commit()


def ensure_action_owner(email: str = "employee@example.com", password: str = "employeepass") -> None:
    with SessionLocal() as db:
        if db.query(User).filter(User.email == email).first():
            return
        owner = User(
            email=email,
            full_name="Action Owner",
            role=UserRole.action_owner.value,
            hashed_password=get_password_hash(password),
        )
        db.add(owner)
        db.commit()


def create_action_for_owner(owner_email: str = "employee@example.com") -> int:
    create_submitted_inspection()
    with SessionLocal() as db:
        owner = db.query(User).filter(User.email == owner_email).first()
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        inspection = db.query(Inspection).first()
        assert owner is not None
        assert inspector is not None
        assert inspection is not None
        action = CorrectiveAction(
            inspection_id=inspection.id,
            title="Repair guard rail",
            severity=ActionSeverity.medium.value,
            status=ActionStatus.open.value,
            started_by_id=inspector.id,
            assigned_to_id=owner.id,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action.id


def create_submitted_inspection(location: str = "Hangar A", *, persist_location: bool = False) -> date:
    submitted_at = datetime.utcnow()
    with SessionLocal() as db:
        template = db.query(ChecklistTemplate).first()
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        assert template is not None
        assert inspector is not None
        location_row: Location | None = None
        if persist_location:
            location_row = db.query(Location).filter(Location.name == location).first()
            if not location_row:
                location_row = Location(name=location)
                db.add(location_row)
                db.flush()
        inspection = Inspection(
            template_id=template.id,
            inspector_id=inspector.id,
            created_by_id=inspector.id,
            status=InspectionStatus.submitted.value,
            location=location,
            location_id=location_row.id if location_row else None,
            started_at=submitted_at,
            submitted_at=submitted_at,
            overall_score=89.5,
            inspection_origin=InspectionOrigin.independent.value,
        )
        db.add(inspection)
        db.flush()
        first_item = template.sections[0].items[0]
        second_item = template.sections[0].items[1]
        fail_response = InspectionResponse(
            inspection_id=inspection.id,
            template_item_id=first_item.id,
            result="fail",
            note="Exit blocked",
        )
        pass_response = InspectionResponse(
            inspection_id=inspection.id,
            template_item_id=second_item.id,
            result="pass",
        )
        db.add_all([fail_response, pass_response])
        db.flush()
        action = CorrectiveAction(
            inspection_id=inspection.id,
            response_id=fail_response.id,
            title="Clear exit",
            severity=ActionSeverity.high.value,
            status=ActionStatus.open.value,
            due_date=submitted_at - timedelta(days=2),
            started_by_id=inspector.id,
            assigned_to_id=inspector.id,
        )
        db.add(action)
        db.commit()
    return submitted_at.date()


def test_login_returns_jwt(client: TestClient) -> None:
    headers = authenticate(client, "admin@example.com", "adminpass")
    assert "Authorization" in headers


def test_template_listing_requires_auth(client: TestClient) -> None:
    response = client.get("/templates/")
    assert response.status_code == 401
    headers = authenticate(client, "admin@example.com", "adminpass")
    authed = client.get("/templates/", headers=headers)
    assert authed.status_code == 200
    assert isinstance(authed.json(), list)


def test_actions_dashboard_available_to_inspector(client: TestClient) -> None:
    headers = authenticate(client, "inspector@example.com", "inspectorpass")
    response = client.get("/dash/actions", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "open_by_severity" in payload
    assert "overdue_actions" in payload


def test_assignee_listing_available_to_all_active_users(client: TestClient) -> None:
    ensure_action_owner()
    headers = authenticate(client, "inspector@example.com", "inspectorpass")
    response = client.get("/users/assignees", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    emails = [user["email"] for user in payload]
    assert "employee@example.com" in emails
    assert "inspector@example.com" not in emails
    assert all(user["role"] == UserRole.action_owner.value for user in payload)


def test_inspection_submission_rules(client: TestClient) -> None:
    headers = authenticate(client, "inspector@example.com", "inspectorpass")

    templates = client.get("/templates/", headers=headers).json()
    template = templates[0]
    template_id = template["id"]
    template_name = template["name"]
    items: List[str] = [item["id"] for section in template["sections"] for item in section["items"]]

    inspection = client.post("/inspections/", json={"template_id": template_id}, headers=headers).json()
    inspection_id = inspection["id"]
    assert inspection["created_by"]["full_name"] == "Inspector One"
    assert inspection["inspection_origin"] == "independent"

    submit = client.put(f"/inspections/{inspection_id}", json={"status": "submitted"}, headers=headers)
    assert submit.status_code == 400

    pass_resp = client.post(
        f"/inspections/{inspection_id}/responses",
        json={"template_item_id": items[0], "result": "pass", "media_urls": []},
        headers=headers,
    )
    assert pass_resp.status_code == 201

    fail_resp = client.post(
        f"/inspections/{inspection_id}/responses",
        json={"template_item_id": items[1], "result": "fail", "media_urls": []},
        headers=headers,
    ).json()

    client.post(
        f"/inspections/{inspection_id}/responses",
        json={"template_item_id": items[2], "result": "pass", "media_urls": []},
        headers=headers,
    )

    submit_without_action = client.put(
        f"/inspections/{inspection_id}",
        json={"status": "submitted"},
        headers=headers,
    )
    assert submit_without_action.status_code == 400

    action_payload = {
        "inspection_id": inspection_id,
        "response_id": fail_resp["id"],
        "title": "Fix exit",
        "description": "Clear obstruction",
        "severity": "high",
        "status": "open",
        "assigned_to_id": inspection["created_by"]["id"],
    }
    action_resp = client.post("/actions/", json=action_payload, headers=headers)
    assert action_resp.status_code == 201
    action_body = action_resp.json()
    assert action_body["started_by"]["email"] == "inspector@example.com"
    assert action_body["assignee"]["id"] == inspection["created_by"]["id"]
    action_id = action_body["id"]


def test_inspection_note_history_tracks_authors(client: TestClient) -> None:
    headers = authenticate(client, "inspector@example.com", "inspectorpass")
    templates = client.get("/templates/", headers=headers).json()
    template_id = templates[0]["id"]
    initial = client.post(
        "/inspections/",
        json={"template_id": template_id, "notes": "Initial walk-through"},
        headers=headers,
    ).json()
    inspection_id = initial["id"]

    update = client.put(
        f"/inspections/{inspection_id}",
        json={"notes": "Follow-up observation"},
        headers=headers,
    )
    assert update.status_code == 200

    detail = client.get(f"/inspections/{inspection_id}", headers=headers).json()
    notes = detail["note_entries"]
    assert [entry["body"] for entry in notes] == ["Initial walk-through", "Follow-up observation"]
    assert all(entry["author"]["email"] == "inspector@example.com" for entry in notes)


def test_action_owner_sees_only_assigned_actions(client: TestClient) -> None:
    ensure_action_owner()
    owner_action_id = create_action_for_owner()
    with SessionLocal() as db:
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        inspection = db.query(Inspection).first()
        assert inspector is not None and inspection is not None
        extra = CorrectiveAction(
            inspection_id=inspection.id,
            title="Extra action",
            severity=ActionSeverity.low.value,
            status=ActionStatus.open.value,
            started_by_id=inspector.id,
            assigned_to_id=inspector.id,
        )
        db.add(extra)
        db.commit()
    headers = authenticate(client, "employee@example.com", "employeepass")
    response = client.get("/actions/", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload, "Expected at least one action for owner"
    owner_assignee = payload[0]["assigned_to_id"]
    assert all(action["assigned_to_id"] == owner_assignee for action in payload)
    action_ids = {action["id"] for action in payload}
    assert owner_action_id in action_ids


def test_action_owner_cannot_update_unassigned_action(client: TestClient) -> None:
    ensure_action_owner()
    headers = authenticate(client, "employee@example.com", "employeepass")
    create_submitted_inspection()
    with SessionLocal() as db:
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        inspection = db.query(Inspection).first()
        assert inspector is not None and inspection is not None
        action = CorrectiveAction(
            inspection_id=inspection.id,
            title="Inspector owned",
            severity=ActionSeverity.low.value,
            status=ActionStatus.open.value,
            started_by_id=inspector.id,
            assigned_to_id=inspector.id,
        )
        db.add(action)
        db.commit()
        action_id = action.id
    response = client.put(
        f"/actions/{action_id}",
        json={"resolution_notes": "Attempted"},
        headers=headers,
    )
    assert response.status_code == 404


def test_action_owner_updates_notes_on_owned_action(client: TestClient) -> None:
    ensure_action_owner()
    owner_action_id = create_action_for_owner()
    headers = authenticate(client, "employee@example.com", "employeepass")
    response = client.put(
        f"/actions/{owner_action_id}",
        json={"resolution_notes": "Investigating root cause"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["resolution_notes"] == "Investigating root cause"
    forbidden = client.put(
        f"/actions/{owner_action_id}",
        json={"due_date": datetime.utcnow().isoformat()},
        headers=headers,
    )
    assert forbidden.status_code == 400


def test_action_note_history_tracks_multiple_authors(client: TestClient) -> None:
    ensure_action_owner()
    owner_action_id = create_action_for_owner()
    owner_headers = authenticate(client, "employee@example.com", "employeepass")
    admin_headers = authenticate(client, "admin@example.com", "adminpass")

    first = client.put(
        f"/actions/{owner_action_id}",
        json={"resolution_notes": "Owner update"},
        headers=owner_headers,
    )
    assert first.status_code == 200

    second = client.put(
        f"/actions/{owner_action_id}",
        json={"resolution_notes": "Admin follow-up"},
        headers=admin_headers,
    )
    assert second.status_code == 200

    detail = client.get(f"/actions/{owner_action_id}", headers=admin_headers).json()
    assert [entry["body"] for entry in detail["note_entries"]] == ["Owner update", "Admin follow-up"]
    authors = [entry["author"]["email"] for entry in detail["note_entries"]]
    assert authors == ["employee@example.com", "admin@example.com"]


def test_action_owner_can_upload_attachment(client: TestClient) -> None:
    ensure_action_owner()
    owner_action_id = create_action_for_owner()
    headers = authenticate(client, "employee@example.com", "employeepass")
    files = {"file": ("evidence.jpg", b"123456", "image/jpeg")}
    response = client.post(
        "/files/",
        params={"action_id": owner_action_id},
        files=files,
        headers=headers,
    )
    assert response.status_code == 201


def test_inspector_cannot_upload_media_for_foreign_inspection(client: TestClient) -> None:
    temp_email = "temp_inspector@example.com"
    temp_password = "temppass"
    create_temp_inspector(temp_email, temp_password)

    temp_headers = authenticate(client, temp_email, temp_password)
    templates = client.get("/templates/", headers=temp_headers).json()
    template_id = templates[0]["id"]
    template_item_id = templates[0]["sections"][0]["items"][0]["id"]

    inspection = client.post("/inspections/", json={"template_id": template_id}, headers=temp_headers).json()
    response = client.post(
        f"/inspections/{inspection['id']}/responses",
        json={"template_item_id": template_item_id, "result": "pass", "media_urls": []},
        headers=temp_headers,
    ).json()

    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 16
    upload_ok = client.post(
        "/files/",
        params={"response_id": response["id"]},
        files={"file": ("proof.png", png_bytes, "image/png")},
        headers=temp_headers,
    )
    assert upload_ok.status_code == 201

    inspector_headers = authenticate(client, "inspector@example.com", "inspectorpass")
    forbidden = client.post(
        "/files/",
        params={"response_id": response["id"]},
        files={"file": ("hack.png", png_bytes, "image/png")},
        headers=inspector_headers,
    )
    assert forbidden.status_code == 403

    own_listing = client.get("/files/", headers=temp_headers)
    assert own_listing.status_code == 200
    assert len(own_listing.json()) == 1

    other_listing = client.get("/files/", headers=inspector_headers)
    assert other_listing.status_code == 200
    assert other_listing.json() == []


def test_reports_endpoint_returns_pdf_for_admin(client: TestClient) -> None:
    report_date = create_submitted_inspection(location="Main Plant")
    headers = authenticate(client, "admin@example.com", "adminpass")
    response = client.get(
        f"/reports/inspections.pdf?start={report_date.isoformat()}&end={report_date.isoformat()}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "inspections-" in response.headers["content-disposition"]


def test_reports_endpoint_forbidden_for_non_reviewer(client: TestClient) -> None:
    report_date = create_submitted_inspection()
    headers = authenticate(client, "inspector@example.com", "inspectorpass")
    response = client.get(
        f"/reports/inspections.pdf?start={report_date.isoformat()}&end={report_date.isoformat()}",
        headers=headers,
    )
    assert response.status_code == 403


def test_generate_inspections_range_pdf_contains_action_data(client: TestClient) -> None:
    report_date = create_submitted_inspection(location="Hangar B")
    with SessionLocal() as db:
        summary = report_service.build_inspections_range_summary(db, report_date, report_date, {})
    assert summary["location_counts"]["Hangar B"] == 1
    assert summary["status_counts"][InspectionStatus.submitted.value] == 1
    assert summary["open_actions_by_severity"][ActionSeverity.high.value] == 1
    assert summary["top_failures"][0]["failures"] == 1


def test_range_summary_honors_location_id_filter(client: TestClient) -> None:
    report_date = create_submitted_inspection(location="Warehouse Alpha", persist_location=True)
    with SessionLocal() as db:
        location = db.query(Location).filter(Location.name == "Warehouse Alpha").first()
        assert location is not None
        matching = report_service.build_inspections_range_summary(
            db,
            report_date,
            report_date,
            {"location_id": location.id},
        )
        assert len(matching["inspections"]) == 1
        assert matching["location_counts"]["Warehouse Alpha"] == 1

        missing = report_service.build_inspections_range_summary(
            db,
            report_date,
            report_date,
            {"location_id": location.id + 999},
        )
        assert len(missing["inspections"]) == 0


def test_assignment_generation_respects_end_date(client: TestClient) -> None:
    headers = authenticate(client, "admin@example.com", "adminpass")
    with SessionLocal() as db:
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        assert inspector is not None
        template = db.query(ChecklistTemplate).first()
        assert template is not None

    start_due_at = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0)
    first_week_start = start_due_at.date() - timedelta(days=start_due_at.weekday())
    second_week_start = first_week_start + timedelta(days=7)
    third_week_start = second_week_start + timedelta(days=7)

    payload = {
        "assigned_to_id": inspector.id,  # type: ignore[attr-defined]
        "template_id": template.id,
        "location": "Hangar B",
        "frequency": "weekly",
        "start_due_at": start_due_at.isoformat(),
        "end_date": (start_due_at.date() + timedelta(days=10)).isoformat(),
    }
    create_resp = client.post("/assignments/", json=payload, headers=headers)
    assert create_resp.status_code == 201
    assignment = create_resp.json()
    assert assignment["frequency"] == "weekly"
    assert assignment["start_due_at"].startswith(start_due_at.date().isoformat())
    assert assignment["end_date"] == (start_due_at.date() + timedelta(days=10)).isoformat()

    resp1 = client.post("/scheduler/generate", params={"weekStart": first_week_start.isoformat()}, headers=headers)
    assert resp1.status_code == 201
    assert len(resp1.json()) == 1

    resp2 = client.post("/scheduler/generate", params={"weekStart": second_week_start.isoformat()}, headers=headers)
    assert resp2.status_code == 201
    assert len(resp2.json()) == 1

    resp3 = client.post("/scheduler/generate", params={"weekStart": third_week_start.isoformat()}, headers=headers)
    assert resp3.status_code == 201
    assert resp3.json() == []

    assignments = client.get("/assignments/", headers=headers).json()
    created = next(item for item in assignments if item["id"] == assignment["id"])
    assert created["active"] is False
    assert created["frequency"] == "weekly"


def test_inspector_can_start_assignment(client: TestClient) -> None:
    admin_headers = authenticate(client, "admin@example.com", "adminpass")
    inspector_headers = authenticate(client, "inspector@example.com", "inspectorpass")
    with SessionLocal() as db:
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        template = db.query(ChecklistTemplate).first()
        assert inspector is not None
        assert template is not None

    start_due_at = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0)
    payload = {
        "assigned_to_id": inspector.id,  # type: ignore[attr-defined]
        "template_id": template.id,
        "location": "Hangar C",
        "frequency": "weekly",
        "start_due_at": start_due_at.isoformat(),
    }
    create_resp = client.post("/assignments/", json=payload, headers=admin_headers)
    assert create_resp.status_code == 201, create_resp.text
    assignment_id = create_resp.json()["id"]

    start_resp = client.post(f"/assignments/{assignment_id}/start", headers=inspector_headers)
    assert start_resp.status_code == 201, start_resp.text
    inspection = start_resp.json()
    assert inspection["template_id"] == template.id
    assert inspection["inspector_id"] == inspector.id
    assert inspection["location"] == "Hangar C"
    assert inspection["inspection_origin"] == "assignment"
    assert inspection["scheduled_inspection_id"] is not None


def test_weekly_overview_reflects_active_assignments(client: TestClient) -> None:
    headers = authenticate(client, "admin@example.com", "adminpass")
    with SessionLocal() as db:
        inspector = db.query(User).filter(User.email == "inspector@example.com").first()
        template = db.query(ChecklistTemplate).first()
        assert inspector is not None
        assert template is not None

    for idx in range(2):
        start_due_at = (datetime.utcnow() + timedelta(days=idx + 1)).replace(microsecond=0)
        payload = {
            "assigned_to_id": inspector.id,  # type: ignore[attr-defined]
            "template_id": template.id,
            "location": f"Hangar Z{idx}",
            "frequency": "weekly",
            "start_due_at": start_due_at.isoformat(),
        }
        resp = client.post("/assignments/", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text

    overview = client.get("/dash/weekly-overview", headers=headers)
    assert overview.status_code == 200, overview.text
    data = overview.json()

    with SessionLocal() as db:
        active_weekly = (
            db.query(Assignment)
            .filter(Assignment.active.is_(True))
            .filter(Assignment.frequency.ilike("weekly"))
            .count()
        )

    assert data["total_expected"] >= active_weekly
    assert "submitted" in data and "approved" in data
