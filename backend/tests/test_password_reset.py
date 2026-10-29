"""Password reset contract: issuance, single-use, hardening guards, audit."""
import hashlib
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import make_user, auth_headers


@pytest.fixture(autouse=True)
def captured_reset_emails(monkeypatch):
    """Background reset emails must not attempt real SMTP in tests; capture
    the raw token the emailer would have delivered instead."""
    from app.services import email as email_mod

    sent: list[dict] = []

    async def _capture(addr, token):
        sent.append({"email": addr, "token": token})

    monkeypatch.setattr(email_mod.email_service, "send_reset_password_email", _capture)
    return sent


async def _issue_token(client: AsyncClient, email: str, sent: list) -> str:
    """Request a reset and return the raw token from the captured email."""
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200, resp.text
    assert sent, "reset email was not scheduled"
    return sent[-1]["token"]


@pytest.mark.asyncio
async def test_forgot_password_no_enumeration(client: AsyncClient):
    await make_user(email="known@test.example")
    known = await client.post("/api/v1/auth/forgot-password", json={"email": "known@test.example"})
    unknown = await client.post("/api/v1/auth/forgot-password", json={"email": "ghost@test.example"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


@pytest.mark.asyncio
async def test_reset_success_and_session_revocation(client: AsyncClient, captured_reset_emails):
    user = await make_user(email="resetme@test.example")
    # Hold a live refresh session
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "Passw0rd123"})
    old_refresh = login.json()["refresh_token"]

    token = await _issue_token(client, user.email, captured_reset_emails)
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewStrong1"},
    )
    assert resp.status_code == 200, resp.text

    # Old refresh token dead
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401
    # New password works
    relogin = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "NewStrong1"})
    assert relogin.status_code == 200


@pytest.mark.asyncio
async def test_reset_rejects_weak_password(client: AsyncClient, captured_reset_emails):
    """The reset path enforces the same complexity rules as registration.

    A 422 is raised by body validation BEFORE the handler runs, so the link
    is not burned — the user can retry with a strong password on the same
    token. Single-use applies to handler execution (success, expiry, banned).
    """
    user = await make_user(email="weakpw@test.example")
    token = await _issue_token(client, user.email, captured_reset_emails)
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "alllowercase1"},
    )
    assert resp.status_code == 422
    # Same token still valid for a strong retry
    retry = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewStrong1"},
    )
    assert retry.status_code == 200


@pytest.mark.asyncio
async def test_reset_token_single_use(client: AsyncClient, captured_reset_emails):
    user = await make_user(email="onuse@test.example")
    token = await _issue_token(client, user.email, captured_reset_emails)
    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "NewStrong1"}
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "NewStrong2"}
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_new_request_invalidates_previous_token(client: AsyncClient, captured_reset_emails):
    user = await make_user(email="rotate@test.example")
    token1 = await _issue_token(client, user.email, captured_reset_emails)
    token2 = await _issue_token(client, user.email, captured_reset_emails)
    stale = await client.post(
        "/api/v1/auth/reset-password", json={"token": token1, "new_password": "NewStrong1"}
    )
    assert stale.status_code == 400
    fresh = await client.post(
        "/api/v1/auth/reset-password", json={"token": token2, "new_password": "NewStrong1"}
    )
    assert fresh.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_per_email_throttle(client: AsyncClient, captured_reset_emails):
    user = await make_user(email="throttle@test.example")
    for _ in range(3):  # limit is 3/hour
        r = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
        assert r.status_code == 200
    flooded = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert flooded.status_code == 429
    # A different account is unaffected
    other = await make_user(email="throttle2@test.example")
    ok = await client.post("/api/v1/auth/forgot-password", json={"email": other.email})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_reset_rejected_for_inactive_and_banned(client: AsyncClient):
    """Confirm re-checks is_active; banned accounts can never reset."""
    from app.api.v1.password_reset import password_reset_tokens

    inactive = await make_user(email="inactive@test.example", is_active=False)
    banned = await make_user(email="banned@test.example", is_banned=True)

    for user in (inactive, banned):
        # Simulate a token issued before the account got restricted
        raw = f"raw-token-for-{user.id}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        password_reset_tokens[digest] = (
            str(user.id), datetime.now(timezone.utc) + timedelta(hours=1),
        )
        resp = await client.post(
            "/api/v1/auth/reset-password", json={"token": raw, "new_password": "NewStrong1"}
        )
        assert resp.status_code == 400, f"{user.email}: {resp.status_code}"


@pytest.mark.asyncio
async def test_reset_writes_audit_log(client: AsyncClient, captured_reset_emails):
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.audit_log import AuditLog

    user = await make_user(email="auditpw@test.example")
    token = await _issue_token(client, user.email, captured_reset_emails)
    await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "NewStrong1"}
    )
    async with async_session() as session:
        logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.action == "reset_password", AuditLog.target_id == user.id
                )
            )
        ).scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "reset_password"
    assert logs[0].target_id == user.id
