from __future__ import annotations

from typing import Dict, List

from fastapi.testclient import TestClient


def authenticate(client: TestClient, username: str, password: str) -> Dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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

    submit_with_action = client.put(
        f"/inspections/{inspection_id}",
        json={"status": "submitted"},
        headers=headers,
    )
    assert submit_with_action.status_code == 200
    assert submit_with_action.json()["status"] == "submitted"
