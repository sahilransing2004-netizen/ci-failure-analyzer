from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
