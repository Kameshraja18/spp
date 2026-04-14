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


def test_intervention_simulator_endpoint():
    resp = client.post(
        "/api/v2/simulate/intervention",
        json={
            "segment_id": "S42",
            "baseline_risk": 0.78,
            "weather_severity": 0.8,
            "congestion_index": 0.7,
            "visibility_score": 0.35,
            "interventions": ["dynamic_speed_limit", "increase_patrols", "improve_lighting"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["segment_id"] == "S42"
    assert "adjusted_risk" in body
    assert "trajectory" in body
    assert len(body["trajectory"]) == 5
