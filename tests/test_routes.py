from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_ingest_empty_list():
    resp = client.post("/ingest", json={"traffic_records": []})
    assert resp.status_code == 200
    assert resp.json().get("count") == 0
