from fastapi.testclient import TestClient

from services.api.main import app
from services.storage import auth as storage_auth

client = TestClient(app)


def test_signup_login_and_profile():
    username = "testuser"
    password = "strongpassword"

    storage_auth.reset_users()

    # Signup
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    assert resp.status_code == 200

    # Login
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    token = data["access_token"]

    # Access protected profile
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/auth/profile", headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("username") == username
