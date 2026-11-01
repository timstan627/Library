"""Admin contract: moderation, users, departments, courses, reports, dashboard."""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, auth_headers


async def admin_headers(client, admin_user):
    return await auth_headers(client, admin_user)


# ---------------------------------------------------------------------------
# Authorization gates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_endpoints_reject_student(client: AsyncClient):
    student = await make_user()
    headers = await auth_headers(client, student)
    for path in (
        "/api/v1/admin/moderation/pending",
        "/api/v1/admin/users",
        "/api/v1/admin/departments",
        "/api/v1/admin/reports",
        "/api/v1/admin/dashboard",
    ):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 403, f"{path} → {resp.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client: AsyncClient):
    for path in ("/api/v1/admin/moderation/pending", "/api/v1/admin/users", "/api/v1/admin/dashboard"):
        resp = await client.get(path)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_moderation_approve_flow(client: AsyncClient, admin_user):
    uploader = await make_user()
    res = await make_resource(uploader, moderation_status="pending")
    headers = await admin_headers(client, admin_user)

    pending = await client.get("/api/v1/admin/moderation/pending", headers=headers)
    assert pending.status_code == 200
    body = pending.json()
    assert body["total"] == 1
    assert body["results"][0]["id"] == res.id

    approve = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    # Now publicly visible
    detail = await client.get(f"/api/v1/resources/{res.id}")
    assert detail.status_code == 200

    # Re-moderation of a non-pending resource → 400
    again = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_moderation_reject_requires_reason(client: AsyncClient, admin_user):
    uploader = await make_user()
    res = await make_resource(uploader, moderation_status="pending")
    headers = await admin_headers(client, admin_user)

    no_reason = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "reject"},
        headers=headers,
    )
    assert no_reason.status_code == 400

    rejected = await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "reject", "rejection_reason": "Low quality"},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Low quality"


@pytest.mark.asyncio
async def test_moderation_stats_and_history(client: AsyncClient, admin_user):
    uploader = await make_user()
    res = await make_resource(uploader, moderation_status="pending")
    headers = await admin_headers(client, admin_user)
    await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate", json={"action": "approve"}, headers=headers
    )

    stats = await client.get("/api/v1/admin/moderation/stats", headers=headers)
    assert stats.status_code == 200
    assert "approved" in stats.json()

    history = await client.get("/api/v1/admin/moderation/history", headers=headers)
    assert history.status_code == 200
    body = history.json()
    assert isinstance(body, dict)
    assert isinstance(body["results"], list)
    assert len(body["results"]) >= 1


# ---------------------------------------------------------------------------
# Users admin
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_users_list_shape(client: AsyncClient, admin_user):
    await make_user()
    await make_user()
    headers = await admin_headers(client, admin_user)
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in ("results", "total", "page", "pages"):
        assert key in body
    assert body["total"] >= 3  # admin + two users
    # No password hashes in admin list
    assert "password_hash" not in body["results"][0]


@pytest.mark.asyncio
async def test_promote_to_trusted(client: AsyncClient, admin_user):
    target = await make_user()
    headers = await admin_headers(client, admin_user)

    resp = await client.post(
        f"/api/v1/admin/users/{target.id}/promote",
        json={"is_trusted": True, "reason": "Contributor"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    promo = resp.json()
    assert promo["is_trusted"] is True
    # Enriched display fields the admin users page consumes (FE/BE sync fix).
    assert promo["display_name"] == target.display_name
    assert promo["role"] == "user"
    assert promo["upload_count"] == 0
    assert promo["approved_count"] == 0

    trusted = await client.get("/api/v1/admin/users/trusted", headers=headers)
    assert trusted.status_code == 200
    row = next(u for u in trusted.json()["results"] if u["user_id"] == target.id)
    assert row["display_name"] == target.display_name
    assert row["role"] == "user"
    assert row["upload_count"] == 0
    assert row["approved_count"] == 0


# ---------------------------------------------------------------------------
# Departments & courses
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_department_crud_and_duplicate_code(client: AsyncClient, admin_user):
    headers = await admin_headers(client, admin_user)

    created = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Computer Science", "code": "CSE"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    dept_id = created.json()["id"]

    dup = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Another CS", "code": "CSE"},
        headers=headers,
    )
    assert dup.status_code == 400

    listed = await client.get("/api/v1/admin/departments", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = await client.put(
        f"/api/v1/admin/departments/{dept_id}",
        json={"name": "CS Dept"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "CS Dept"

    # Public list sees it
    public = await client.get("/api/v1/departments")
    assert public.status_code == 200
    assert any(d["code"] == "CSE" for d in public.json())

    deleted = await client.delete(f"/api/v1/admin/departments/{dept_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_course_crud(client: AsyncClient, admin_user):
    headers = await admin_headers(client, admin_user)
    dept = await client.post(
        "/api/v1/admin/departments", json={"name": "ECE", "code": "ECE"}, headers=headers
    )
    dept_id = dept.json()["id"]

    created = await client.post(
        "/api/v1/admin/courses",
        json={"name": "Data Structures", "code": "CS201", "department_id": dept_id},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["department_name"] == "ECE"
    course_id = created.json()["id"]

    dup = await client.post(
        "/api/v1/admin/courses",
        json={"name": "Dup", "code": "CS201", "department_id": dept_id},
        headers=headers,
    )
    assert dup.status_code == 400

    listed = await client.get("/api/v1/admin/courses", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    public_list = await client.get("/api/v1/courses")
    assert public_list.status_code == 200
    assert any(c["code"] == "CS201" for c in public_list.json())

    public_detail = await client.get(f"/api/v1/courses/{course_id}")
    assert public_detail.status_code == 200

    deleted = await client.delete(f"/api/v1/admin/courses/{course_id}", headers=headers)
    assert deleted.status_code == 204


# ---------------------------------------------------------------------------
# Reports & dashboard
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_report_lifecycle(client: AsyncClient, admin_user):
    reporter = await make_user()
    owner = await make_user()
    res = await make_resource(owner)
    reporter_headers = await auth_headers(client, reporter)
    admin_h = await admin_headers(client, admin_user)

    created = await client.post(
        "/api/v1/reports/",
        json={"resource_id": res.id, "reason": "copyright", "description": "Stolen content"},
        headers=reporter_headers,
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    dup = await client.post(
        "/api/v1/reports/",
        json={"resource_id": res.id, "reason": "copyright"},
        headers=reporter_headers,
    )
    assert dup.status_code == 400

    listed = await client.get("/api/v1/admin/reports", headers=admin_h)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    resolved = await client.put(
        f"/api/v1/admin/reports/{report_id}",
        json={"action": "resolved", "resolution_note": "Removed"},
        headers=admin_h,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_dashboard_shapes(client: AsyncClient, admin_user):
    headers = await admin_headers(client, admin_user)
    full = await client.get("/api/v1/admin/dashboard", headers=headers)
    assert full.status_code == 200
    lite = await client.get("/api/v1/admin/dashboard/cache", headers=headers)
    assert lite.status_code == 200


@pytest.mark.asyncio
async def test_seed_endpoint_idempotent(client: AsyncClient, admin_user):
    headers = await admin_headers(client, admin_user)
    first = await client.post("/api/v1/admin/system/seed", headers=headers)
    assert first.status_code == 200, first.text
    second = await client.post("/api/v1/admin/system/seed", headers=headers)
    assert second.status_code == 200
