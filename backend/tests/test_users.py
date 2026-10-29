"""Users contract: profile get/update, storage, change-password."""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, auth_headers, reloaded


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    user = await make_user(email="me@test.example")
    headers = await auth_headers(client, user)
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@test.example"
    assert "password_hash" not in body
    assert "mfa_secret" not in body


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    user = await make_user()
    headers = await auth_headers(client, user)
    resp = await client.put(
        "/api/v1/users/me",
        json={"display_name": "Renamed User", "avatar_url": "https://example.com/a.png"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Renamed User"
    assert body["avatar_url"] == "https://example.com/a.png"

    # Unknown/privilege fields are rejected (extra="forbid"), not ignored
    tamper = await client.put(
        "/api/v1/users/me", json={"role": "admin"}, headers=headers
    )
    assert tamper.status_code == 422


@pytest.mark.asyncio
async def test_storage_info(client: AsyncClient):
    user = await make_user()
    await make_resource(user, file_size=1234)
    headers = await auth_headers(client, user)
    resp = await client.get("/api/v1/users/me/storage", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("used_bytes") == 1234 or body.get("used") == 1234


@pytest.mark.asyncio
async def test_change_password_invalidates_sessions(client: AsyncClient):
    user = await make_user()
    headers = await auth_headers(client, user)
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    old_refresh = login.json()["refresh_token"]

    change = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "Passw0rd123", "new_password": "NewPassw0rd1"},
        headers=headers,
    )
    assert change.status_code == 200, change.text

    # Refresh sessions were revoked server-side: old refresh token must fail.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401

    # New password works
    new_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "NewPassw0rd1"}
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_requires_correct_current(client: AsyncClient):
    user = await make_user()
    headers = await auth_headers(client, user)
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "WrongPass1", "new_password": "NewPassw0rd1"},
        headers=headers,
    )
    assert resp.status_code in (400, 401)
