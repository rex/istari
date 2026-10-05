from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import OWNER_PASSWORD, OWNER_USERNAME


async def test_protected_routes_require_login(client: AsyncClient) -> None:
    response = await client.get("/api/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "unauthenticated" and "request_id" in body


async def test_health_needs_no_auth_and_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


async def test_wrong_password_is_rejected_and_throttled(client: AsyncClient, owner: None) -> None:
    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD[::-1]}
        )
        assert response.status_code == 401
    locked = await client.post(
        "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
    )
    assert locked.status_code == 429
    assert locked.json()["details"]["retry_after_seconds"] > 0


async def test_login_sets_httponly_cookie_and_csrf_guards_mutations(
    client: AsyncClient, owner: None
) -> None:
    response = await client.post(
        "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "istari_session=" in cookie
    csrf = response.json()["csrf_token"]

    # Reads work with the cookie alone.
    assert (await client.get("/api/me")).status_code == 200
    # Writes need the synchronizer token...
    assert (await client.patch("/api/settings", json={"timezone": "UTC"})).status_code == 403
    # ...and reject a wrong one, and a cross-site Origin.
    bad = await client.patch(
        "/api/settings", json={"timezone": "UTC"}, headers={"x-csrf-token": "nope"}
    )
    assert bad.status_code == 403
    cross = await client.patch(
        "/api/settings",
        json={"timezone": "UTC"},
        headers={"x-csrf-token": csrf, "origin": "https://evil.example"},
    )
    assert cross.status_code == 403
    ok = await client.patch(
        "/api/settings", json={"timezone": "UTC"}, headers={"x-csrf-token": csrf}
    )
    assert ok.status_code == 200 and ok.json()["timezone"] == "UTC"


async def test_logout_revokes_the_session(auth_client: AsyncClient) -> None:
    assert (await auth_client.post("/api/auth/logout")).status_code == 200
    # The client still holds the (now revoked) cookie value.
    assert (await auth_client.get("/api/me")).status_code == 401


async def test_security_headers_on_every_response(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "script-src 'self'" in response.headers["content-security-policy"]
