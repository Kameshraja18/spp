from fastapi.testclient import TestClient

from services.api.main import app
from services.storage import auth as storage_auth

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_root_redirects_to_ui():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (307, 308)
    assert resp.headers.get("location") == "/ui"


def test_ui_requires_auth_redirects_to_login():
    storage_auth.reset_users()
    resp = client.get("/ui", follow_redirects=False)
    assert resp.status_code in (307, 308)
    assert resp.headers.get("location") == "/login"


def test_ui_allows_authenticated_cookie_session():
    storage_auth.reset_users()
    client.post("/auth/signup", json={"username": "uiuser", "password": "strongpass"})
    login = client.post("/auth/login", json={"username": "uiuser", "password": "strongpass"})
    assert login.status_code == 200

    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "Road Safety Intelligence" in resp.text


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
