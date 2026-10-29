"""Authentication contract: register, login, refresh, logout, me, MFA."""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "NewUser@Test.example", "password": "Passw0rd123", "display_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "newuser@test.example"  # normalized lowercase
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_register_duplicate_email_400(client: AsyncClient):
    payload = {"email": "dup@test.example", "password": "Passw0rd123"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@test.example", "password": "alllowercase1"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_me(client: AsyncClient):
    user = await make_user(email="login@test.example")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == user.email


@pytest.mark.asyncio
async def test_login_wrong_password_401(client: AsyncClient):
    user = await make_user(email="wrongpw@test.example")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "WrongPass1"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_banned_403(client: AsyncClient):
    user = await make_user(email="banned@test.example", is_banned=True, is_active=False)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_rotation(client: AsyncClient):
    user = await make_user(email="refresh@test.example")
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    old_refresh = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # Old refresh token must not work after rotation.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_refresh_missing_body_400(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient):
    user = await make_user(email="logout@test.example")
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    out = await client.post("/api/v1/auth/logout", headers=headers)
    assert out.status_code == 200

    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    # HTTPBearer without auto_error raises 403 for missing credentials.
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_banned_user_token_treated_anonymous(client: AsyncClient):
    """A user banned after login must not pass required auth anymore."""
    user = await make_user(email="bannedlater@test.example")
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    token = login.json()["access_token"]

    from app.core.database import async_session
    async with async_session() as session:
        session.add(user)
        user.is_banned = True
        user.is_active = False
        await session.commit()

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mfa_setup_verify_disable_flow(client: AsyncClient):
    user = await make_user(email="mfa@test.example")
    headers = await auth_headers_flow(client, user)

    setup = await client.post("/api/v1/auth/setup-mfa", headers=headers)
    assert setup.status_code == 200
    body = setup.json()
    assert body["secret"] and body["qr_code_base64"].startswith("iVBOR")

    # Enable requires a valid code; invalid code → 400.
    bad = await client.post("/api/v1/auth/verify-mfa", json={"code": "000000"}, headers=headers)
    assert bad.status_code == 400

    import pyotp
    totp = pyotp.TOTP(body["secret"])
    good = await client.post(
        "/api/v1/auth/verify-mfa", json={"code": totp.now()}, headers=headers
    )
    assert good.status_code == 200

    # Login now requires MFA.
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"}
    )
    assert login.json()["requires_mfa"] is True

    # Disable with valid code.
    disable = await client.post(
        "/api/v1/auth/disable-mfa", json={"code": totp.now()}, headers=headers
    )
    assert disable.status_code == 200


async def auth_headers_flow(client: AsyncClient, user) -> dict:
    from tests.conftest import auth_headers
    return await auth_headers(client, user)
