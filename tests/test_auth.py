"""
Authentication API tests.
"""


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_login_success(client):
    res = client.post("/api/auth/login", json={"email": "admin@sovereign.local", "password": "admin"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "admin@sovereign.local"
    assert data["user"]["role"] == "super_admin"


def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={"email": "admin@sovereign.local", "password": "wrongpassword"})
    assert res.status_code == 401


def test_get_me(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "admin@sovereign.local"


def test_logout(client, auth_headers):
    res = client.post("/api/auth/logout", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "logged_out"
