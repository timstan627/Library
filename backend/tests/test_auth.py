"""Authentication contract: register, login, refresh, logout, me, MFA."""
import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.middleware import AuthRateLimiter
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
async def test_refresh_missing_body_422(client: AsyncClient):
    """Missing refresh_token is a request-validation failure → 422.

    The handler takes a typed RefreshRequest, so FastAPI rejects the empty
    body before the handler runs (was a manual 400 with `dict`).
    """
    resp = await client.post("/api/v1/auth/refresh", json={})
    assert resp.status_code == 422
    # No body at all is also a validation failure, not a 500
    no_body = await client.post("/api/v1/auth/refresh")
    assert no_body.status_code == 422


# ---------------------------------------------------------------------------
# Brute-force lockout: per-(ip, email) AND account-wide (email-only) windows
# ---------------------------------------------------------------------------
def test_lockout_per_ip_window_unit():
    limiter = AuthRateLimiter(max_attempts=5, lockout_minutes=15)
    for _ in range(5):
        limiter.record_failure("10.0.0.1", "unit@x.example")
    with pytest.raises(HTTPException) as exc:
        limiter.check_and_record("10.0.0.1", "unit@x.example")
    assert exc.value.status_code == 429
    # A different IP for the same email is not blocked by the per-IP window
    limiter.check_and_record("10.0.0.2", "unit@x.example")


def test_lockout_account_wide_window_unit():
    """Distributed brute force (rotating IPs) trips the email-only budget."""
    limiter = AuthRateLimiter(max_attempts=5, lockout_minutes=15)
    budget = 5 * AuthRateLimiter.ACCOUNT_WIDE_MULTIPLIER
    for i in range(budget):
        ip = f"10.{i // 255}.{i % 255}.9"
        # Each IP stays below its own per-IP limit (1 failure each)
        limiter.check_and_record(ip, "victim@x.example")
        limiter.record_failure(ip, "victim@x.example")
    # Budget exhausted → a brand-new IP is blocked on the account
    with pytest.raises(HTTPException) as exc:
        limiter.check_and_record("10.9.9.9", "victim@x.example")
    assert exc.value.status_code == 429
    # A different account from that same fresh IP is unaffected
    limiter.check_and_record("10.9.9.9", "bystander@x.example")


def test_lockout_clear_resets_both_windows():
    limiter = AuthRateLimiter(max_attempts=5, lockout_minutes=15)
    for _ in range(5):
        limiter.record_failure("10.0.0.1", "clear@x.example")
    for _ in range(15):
        limiter.record_failure("10.2.0.1", "clear@x.example")
    with pytest.raises(HTTPException):
        limiter.check_and_record("10.0.0.1", "clear@x.example")
    limiter.clear("10.0.0.1", "clear@x.example")
    limiter.check_and_record("10.0.0.1", "clear@x.example")  # no raise


def test_sweep_windowed_drops_stale_and_caps():
    """Global eviction: stale buckets go, newest survive past the cap."""
    from app.core.middleware import sweep_windowed

    now = 1_000_000.0
    d = {
        "fresh-1": [now - 10.0],
        "stale": [now - 10_000.0],   # fully outside the window
        "empty": [],                  # touched-then-pruned bucket
    }
    for i in range(5):
        d[f"bulk-{i}"] = [now - 20.0 - i]

    sweep_windowed(d, window=60.0, now=now, max_keys=4)

    assert "stale" not in d and "empty" not in d  # 1) expired/empty dropped
    assert len(d) == 4                            # 2) hard cap enforced
    assert "fresh-1" in d                          # newest buckets survive
    # The four kept buckets are the newest ones (fresh-1 + bulk-0..2)
    assert set(d) == {"fresh-1", "bulk-0", "bulk-1", "bulk-2"}


def test_sweep_windowed_noop_below_cap():
    from app.core.middleware import sweep_windowed

    d = {"a": [1.0], "b": [2.0]}
    sweep_windowed(d, window=60.0, now=1_000_000.0, max_keys=100)
    assert d == {"a": [1.0], "b": [2.0]}  # untouched — cheap no-op path


@pytest.mark.asyncio
async def test_login_lockout_account_wide_rotating_ips(client: AsyncClient):
    """End-to-end: rotating XFF IPs cannot evade the per-account lockout.

    httpx's ASGITransport presents 127.0.0.1 — a default-trusted proxy — so
    X-Forwarded-For is honored exactly as behind nginx.
    """
    user = await make_user(email="rotating@test.example")
    for i in range(15):  # 3 × per-IP budget of failed attempts
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "WrongPass1"},
            headers={"X-Forwarded-For": f"203.0.113.{i}"},
        )
        assert r.status_code == 401, f"attempt {i} → {r.status_code}"

    # Account budget exhausted → a brand-new IP is locked out of the ACCOUNT,
    # even with the CORRECT password.
    locked = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Passw0rd123"},
        headers={"X-Forwarded-For": "203.0.113.200"},
    )
    assert locked.status_code == 429
    assert "account" in locked.json()["detail"].lower()

    # A different account from that same fresh IP is unaffected
    other = await make_user(email="rotating-other@test.example")
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": other.email, "password": "Passw0rd123"},
        headers={"X-Forwarded-For": "203.0.113.200"},
    )
    assert ok.status_code == 200


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
