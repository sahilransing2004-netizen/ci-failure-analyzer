from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)
HEADERS = {"X-Webhook-Token": "test-token"}
PAYLOAD = {
    "repo": "sahil/demo",
    "workflow": "build",
    "run_id": 1,
    "log": "ERROR: requirements.txt not found",
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_rejects_missing_token():
    response = client.post("/webhook/failure", json=PAYLOAD)
    assert response.status_code == 401


def test_webhook_rejects_wrong_token():
    response = client.post(
        "/webhook/failure", json=PAYLOAD, headers={"X-Webhook-Token": "wrong"}
    )
    assert response.status_code == 401


def test_webhook_stores_and_analyzes(monkeypatch):
    monkeypatch.setattr(
        main, "analyze_failure", lambda repo, workflow, log: "Root Cause: test"
    )
    response = client.post("/webhook/failure", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["analysis"] == "Root Cause: test"

    detail = client.get(f"/failures/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["repo"] == "sahil/demo"


def test_get_missing_failure_returns_404():
    response = client.get("/failures/999999")
    assert response.status_code == 404
