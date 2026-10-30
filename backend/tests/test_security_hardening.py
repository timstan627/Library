"""Iteration-4 security hardening tests.

Policy: an audit-log failure must NEVER fail the user action — audit is
observability, not a gate. Every admin mutation site wraps its audit write in
try/except + logger.exception. These tests prove it by making AuditLog
construction blow up and asserting the action still succeeds.
"""
from httpx import AsyncClient

from app.models.audit_log import AuditLog
from tests.conftest import make_resource, make_user, auth_headers


def _break_audit_log(monkeypatch):
    def _boom(self, *args, **kwargs):
        raise RuntimeError("audit storage unavailable (simulated)")

    monkeypatch.setattr(AuditLog, "__init__", _boom)


async def test_moderate_succeeds_when_audit_fails(
    client: AsyncClient, admin_user, student_user, monkeypatch
):
    _break_audit_log(monkeypatch)
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user, moderation_status="pending")

    resp = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"audit failure must not fail moderation: {resp.status_code} {resp.text}"
    )


async def test_promote_succeeds_when_audit_fails(
    client: AsyncClient, admin_user, monkeypatch
):
    _break_audit_log(monkeypatch)
    headers = await auth_headers(client, admin_user)
    target = await make_user()

    resp = await client.post(
        f"/api/v1/admin/users/{target.id}/promote",
        json={"is_trusted": True, "reason": "Contributor"},
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"audit failure must not fail promotion: {resp.status_code} {resp.text}"
    )


async def test_department_update_succeeds_when_audit_fails(
    client: AsyncClient, admin_user, monkeypatch
):
    _break_audit_log(monkeypatch)
    headers = await auth_headers(client, admin_user)
    created = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Audit Boom Dept", "code": "ABD"},
        headers=headers,
    )
    # Create also writes an audit row — must survive too.
    assert created.status_code == 201, created.text
    dept_id = created.json()["id"]

    upd = await client.put(
        f"/api/v1/admin/departments/{dept_id}",
        json={"description": "still works"},
        headers=headers,
    )
    assert upd.status_code == 200, upd.text
