from __future__ import annotations

from typing import Dict, List

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.entities import User, UserRole


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


def test_inspection_submission_rules(client: TestClient) -> None:
    headers = authenticate(client, "inspector@example.com", "inspectorpass")

    templates = client.get("/templates/", headers=headers).json()
    template_id = templates[0]["id"]
    items: List[str] = [item["id"] for section in templates[0]["sections"] for item in section["items"]]

    inspection = client.post("/inspections/", json={"template_id": template_id}, headers=headers).json()
    inspection_id = inspection["id"]
    assert inspection["created_by"]["full_name"] == "Inspector One"

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
    }
    action_resp = client.post("/actions/", json=action_payload, headers=headers)
    assert action_resp.status_code == 201
    action_body = action_resp.json()
    assert action_body["started_by"]["email"] == "inspector@example.com"
    action_id = action_body["id"]

    close_without_evidence = client.put(
        f"/actions/{action_id}",
        json={"status": "closed", "resolution_notes": "Cleared obstruction"},
        headers=headers,
    )
    assert close_without_evidence.status_code == 400

    upload_action_media = client.post(
        "/files/",
        params={"action_id": action_id},
        files={"file": ("evidence.jpg", b"proof", "image/jpeg")},
        headers=headers,
    )
    assert upload_action_media.status_code == 201

    close_without_notes = client.put(
        f"/actions/{action_id}",
        json={"status": "closed"},
        headers=headers,
    )
    assert close_without_notes.status_code == 400

    close_with_notes = client.put(
        f"/actions/{action_id}",
        json={"status": "closed", "resolution_notes": "Cleared obstruction"},
        headers=headers,
    )
    assert close_with_notes.status_code == 200
    assert close_with_notes.json()["closed_by"]["email"] == "inspector@example.com"
    assert close_with_notes.json()["resolution_notes"] == "Cleared obstruction"

    submit_with_action = client.put(
        f"/inspections/{inspection_id}",
        json={"status": "submitted"},
        headers=headers,
    )
    assert submit_with_action.status_code == 200
    assert submit_with_action.json()["status"] == "submitted"


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

    upload_ok = client.post(
        "/files/",
        params={"response_id": response["id"]},
        files={"file": ("proof.txt", b"ok", "text/plain")},
        headers=temp_headers,
    )
    assert upload_ok.status_code == 201

    inspector_headers = authenticate(client, "inspector@example.com", "inspectorpass")
    forbidden = client.post(
        "/files/",
        params={"response_id": response["id"]},
        files={"file": ("hack.txt", b"x", "text/plain")},
        headers=inspector_headers,
    )
    assert forbidden.status_code == 403

    own_listing = client.get("/files/", headers=temp_headers)
    assert own_listing.status_code == 200
    assert len(own_listing.json()) == 1

    other_listing = client.get("/files/", headers=inspector_headers)
    assert other_listing.status_code == 200
    assert other_listing.json() == []
