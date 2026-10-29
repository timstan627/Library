"""Iteration-2 reliability tests: M5, M6, M10, M12-residual.

Red-first per ECC tdd-workflow: every test here fails against the pre-fix code
and encodes the contract the fix must satisfy.
"""
import json

from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.report import Report
from tests.conftest import (
    make_resource,
    auth_headers,
    reloaded,
)


# --------------------------------------------------------------------------
# M5: moderation must ignore soft-deleted resources and close the
# check-then-act race on the pending status
# --------------------------------------------------------------------------

async def test_moderate_soft_deleted_pending_resource_404s(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user, moderation_status="pending", is_deleted=True)

    resp = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )

    assert resp.status_code == 404, (
        f"soft-deleted pending resource was moderated: {resp.status_code} {resp.text}"
    )


async def test_moderate_approve_writes_audit_with_real_target(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user, moderation_status="pending")

    resp = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    async with _session() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "approve_resource",
                        AuditLog.target_id == str(res.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1, "approve audit missing or mis-targeted"


async def test_moderate_double_submission_rejected(
    client: AsyncClient, admin_user, student_user
):
    """Sequential double-moderation must fail; the atomic write also closes
    the concurrent race (same WHERE clause)."""
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user, moderation_status="pending")

    first = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert second.status_code == 400, second.text


# --------------------------------------------------------------------------
# M6: resolve_report must refuse to overwrite an already-resolved report
# --------------------------------------------------------------------------

async def _make_report(student_user, resource) -> Report:
    report = Report(
        reporter_id=str(student_user.id),
        resource_id=str(resource.id),
        reason="copyright",
    )
    from app.core.database import async_session

    async with async_session() as session:
        session.add(report)
        await session.commit()
        await session.refresh(report)
    return report


async def test_resolve_report_twice_409(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user)
    report = await _make_report(student_user, res)

    first = await client.put(
        f"/api/v1/admin/reports/{report.id}",
        json={"action": "resolved", "resolution_note": "handled"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "resolved"

    second = await client.put(
        f"/api/v1/admin/reports/{report.id}",
        json={"action": "dismissed", "resolution_note": "changed my mind"},
        headers=headers,
    )
    assert second.status_code == 409, (
        f"already-resolved report was overwritten: {second.status_code} {second.text}"
    )

    # Original resolution is untouched.
    fresh = await _fetch(Report, report.id)
    assert fresh.status == "resolved"
    assert fresh.resolution_note == "handled"


# --------------------------------------------------------------------------
# M10: SMTP must use a timeout and close the socket even on send failure
# --------------------------------------------------------------------------

async def test_smtp_uses_timeout_and_closes_on_error(monkeypatch):
    import app.services.email as email_mod

    calls: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            calls["host"] = host
            calls["port"] = port
            calls["timeout"] = timeout

        def starttls(self):
            calls["starttls"] = True

        def login(self, user, password):
            calls["login"] = True

        def sendmail(self, *a, **k):
            raise RuntimeError("smtp exploded mid-send")

        def quit(self):
            calls["quit"] = True

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.quit()
            return False

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)

    svc = email_mod.EmailService()
    svc.smtp_user = "user@example.com"
    svc.smtp_password = "secret"

    # Must not raise (email failures are logged, not fatal).
    svc.send_reset_password_email("to@example.com", "token123")

    assert calls.get("timeout") is not None, "SMTP created without a timeout (can hang forever)"
    assert calls.get("quit") is True, "socket left open after send failure"


# --------------------------------------------------------------------------
# M12-residual: backup upload must persist backup message ids on the resource
# --------------------------------------------------------------------------

async def test_backup_info_persisted_to_resource(student_user):
    from app.services.telegram import telegram_service

    res = await make_resource(student_user)

    await telegram_service._persist_backup_info(
        primary_message_id=res.telegram_message_id,
        primary_channel_id=res.telegram_channel_id,
        backup_file_id="backup-file-xyz",
        backup_message_id=424242,
    )

    fresh = await reloaded(res)
    assert fresh.backup_telegram_file_id == "backup-file-xyz"
    assert fresh.backup_telegram_message_id == 424242


async def test_persist_backup_info_noop_for_unknown_message(student_user):
    """DB-backup uploads (not resources) must not crash the background task."""
    from app.services.telegram import telegram_service

    await telegram_service._persist_backup_info(
        primary_message_id=999999999,
        primary_channel_id=-100123,
        backup_file_id="x",
        backup_message_id=1,
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _session():
    from app.core.database import async_session

    return async_session()


async def _fetch(model, id_):
    from app.core.database import async_session

    async with async_session() as session:
        return await session.get(model, id_)
