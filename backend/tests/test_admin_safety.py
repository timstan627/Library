"""Iteration-1 safety tests: H2, H3, H4, H5 (+ M9, M16, M17 in the same files).

Red-first per ECC tdd-workflow: every test here fails against the pre-fix code
and encodes the contract the fix must satisfy.
"""
import io
import json
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select, event

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.resource import Resource
from tests.conftest import make_resource, auth_headers, make_user, make_department, fake_telegram_upload


async def _make_dept_course(client: AsyncClient, headers, dept_code="DPT"):
    dept_resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": f"Dept {dept_code}", "code": dept_code},
        headers=headers,
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]
    course_resp = await client.post(
        "/api/v1/admin/courses",
        json={
            "name": f"Course {dept_code}",
            "code": f"{dept_code}101",
            "department_id": dept_id,
        },
        headers=headers,
    )
    assert course_resp.status_code == 201, course_resp.text
    return dept_id, course_resp.json()["id"]


# --------------------------------------------------------------------------
# H2: admin course/department delete must not hard-cascade resources
# --------------------------------------------------------------------------

async def test_course_delete_refuses_when_resources_exist(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    _, course_id = await _make_dept_course(client, headers, "CRA")
    res = await make_resource(student_user, course_id=course_id)

    resp = await client.delete(f"/api/v1/admin/courses/{course_id}", headers=headers)

    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
    detail = resp.json()["detail"]
    assert "1" in detail  # mentions the resource count

    # Resource survives, still soft-alive.
    fresh = await client.get(f"/api/v1/admin/resources", headers=headers)
    ids = [r["id"] for r in fresh.json()["results"]]
    assert str(res.id) in ids


async def test_course_delete_succeeds_when_no_resources(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    _, course_id = await _make_dept_course(client, headers, "CRB")

    resp = await client.delete(f"/api/v1/admin/courses/{course_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    # Audit entry written for the deletion.
    async with _session() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "delete_course",
                        AuditLog.target_id == course_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


async def test_department_delete_refuses_when_courses_exist(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    dept_id, course_id = await _make_dept_course(client, headers, "DRB")
    res = await make_resource(student_user, course_id=course_id)

    resp = await client.delete(f"/api/v1/admin/departments/{dept_id}", headers=headers)

    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
    assert str(res.id) in [
        r["id"] for r in (await client.get("/api/v1/admin/resources", headers=headers)).json()["results"]
    ]


async def test_department_delete_succeeds_when_empty(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    dept_resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Empty Dept", "code": "DRY"},
        headers=headers,
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    resp = await client.delete(f"/api/v1/admin/departments/{dept_id}", headers=headers)
    assert resp.status_code == 204, resp.text


async def test_department_delete_refuses_when_resources_bound_directly(
    client: AsyncClient, admin_user, student_user
):
    """Uploads bind department_id directly (no course row). The delete guard
    must count those children too — pre-fix this hits the enforced FK and
    returns a 500 IntegrityError instead of a 409."""
    headers = await auth_headers(client, admin_user)
    dept = await make_department(name="Direct Bind Dept", code="DBR")
    res = await make_resource(student_user, department_id=dept.id)

    resp = await client.delete(f"/api/v1/admin/departments/{dept.id}", headers=headers)

    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
    assert "resource" in resp.json()["detail"].lower()

    # The department row survives and so does the resource.
    listed = await client.get("/api/v1/admin/departments", headers=headers)
    assert dept.code in [d["code"] for d in listed.json()["results"]]
    assert str(res.id) in [
        r["id"] for r in (await client.get("/api/v1/admin/resources", headers=headers)).json()["results"]
    ]


async def test_department_delete_refuses_on_soft_deleted_resources(
    client: AsyncClient, admin_user, student_user
):
    """H2 rule for courses counts every child row, soft-deleted included;
    the direct-binding guard must behave the same (the FK still dangles)."""
    headers = await auth_headers(client, admin_user)
    dept = await make_department(name="Soft Bound Dept", code="SBD")
    await make_resource(student_user, department_id=dept.id, is_deleted=True)

    resp = await client.delete(f"/api/v1/admin/departments/{dept.id}", headers=headers)

    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
    assert "resource" in resp.json()["detail"].lower()


async def test_admin_courses_list_reports_resource_count(
    client: AsyncClient, admin_user, student_user
):
    """The course page gates deletion on real blast radius, so the list
    response must carry a batched resource_count (additive contract)."""
    headers = await auth_headers(client, admin_user)
    _, bound_course = await _make_dept_course(client, headers, "RCC")
    _, empty_course = await _make_dept_course(client, headers, "RCX")
    await make_resource(student_user, course_id=bound_course)
    await make_resource(student_user, course_id=bound_course, title="Second Notes")

    resp = await client.get("/api/v1/admin/courses", headers=headers)
    assert resp.status_code == 200, resp.text
    by_code = {c["code"]: c["resource_count"] for c in resp.json()["results"]}
    assert by_code["RCC101"] == 2
    assert by_code["RCX101"] == 0


async def test_upload_rejects_inactive_department(
    client: AsyncClient, admin_user, monkeypatch
):
    """A deactivated department is hidden from the upload form, so its name
    in an upload request is stale client data — reject with 400 instead of
    binding a fresh resource to a retired department."""
    headers = await auth_headers(client, admin_user)
    dept_resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Retired Dept", "code": "RTD"},
        headers=headers,
    )
    assert dept_resp.status_code == 201, dept_resp.text
    upd = await client.put(
        f"/api/v1/admin/departments/{dept_resp.json()['id']}",
        json={"is_active": False},
        headers=headers,
    )
    assert upd.status_code == 200, upd.text

    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    own_headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
        data={
            "title": "Bound Notes",
            "course_code": "CS101",
            "description": "",
            "visibility": "public",
            "department": "Retired Dept",
        },
        headers=own_headers,
    )
    assert resp.status_code == 400, f"expected 400, got {resp.status_code}: {resp.text}"
    assert "inactive" in resp.json()["detail"].lower()

    # No resource row was created for the retired department.
    fresh = (await client.get("/api/v1/admin/resources", headers=headers)).json()["results"]
    assert all(r["title"] != "Bound Notes" for r in fresh)


# --------------------------------------------------------------------------
# H3: public course endpoints must not leak internal error text
# --------------------------------------------------------------------------

async def test_public_courses_500_is_generic(
    client: AsyncClient, monkeypatch
):
    from sqlalchemy.ext.asyncio import AsyncSession

    sentinel = "SENTRY-LEAK-xyz sqlite malformed"

    async def boom(self, *a, **k):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(AsyncSession, "execute", boom)
    resp = await client.get("/api/v1/courses")
    assert resp.status_code == 500
    assert sentinel not in resp.text
    assert resp.json()["detail"] != sentinel


# --------------------------------------------------------------------------
# M17: public course detail must not serve deactivated courses
# --------------------------------------------------------------------------

async def test_public_course_detail_404_for_inactive(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    _, course_id = await _make_dept_course(client, headers, "INA")

    toggle = await client.patch(f"/api/v1/admin/courses/{course_id}/toggle", headers=headers)
    if toggle.status_code >= 400:
        # No toggle route: deactivate via update payload instead.
        upd = await client.put(
            f"/api/v1/admin/courses/{course_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert upd.status_code == 200, upd.text

    resp = await client.get(f"/api/v1/courses/{course_id}")
    assert resp.status_code == 404, f"expected 404 for inactive course, got {resp.status_code}"


async def test_public_department_detail_404_for_inactive(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    dept = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Inactive Pub Dept", "code": "IPD"},
        headers=headers,
    )
    assert dept.status_code == 201, dept.text
    dept_id = dept.json()["id"]

    upd = await client.put(
        f"/api/v1/admin/departments/{dept_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert upd.status_code == 200, upd.text

    resp = await client.get(f"/api/v1/departments/{dept_id}")
    assert resp.status_code == 404, f"expected 404 for inactive department, got {resp.status_code}"


# --------------------------------------------------------------------------
# H4: admin user list must not run 2 queries per user
# --------------------------------------------------------------------------

async def test_admin_users_list_query_count_is_bounded(
    client: AsyncClient, admin_user, student_user, trusted_user
):
    headers = await auth_headers(client, admin_user)
    # Give the users some resources so the counts are non-trivial.
    await make_resource(student_user)
    await make_resource(trusted_user)

    statements: list[str] = []

    def _track(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    from sqlalchemy import event as sa_event
    from app.core.database import engine

    sa_event.listen(engine.sync_engine, "before_cursor_execute", _track)
    try:
        resp = await client.get("/api/v1/admin/users?page=1&page_size=50", headers=headers)
    finally:
        sa_event.remove(engine.sync_engine, "before_cursor_execute", _track)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3

    # Pre-fix algorithm runs 2 count queries per listed user (2*N + 2).
    # Post-fix runs a constant handful. For N=3: current = 8; bound below fails red.
    assert len(statements) < 8, f"admin user list issued {len(statements)} queries"


# --------------------------------------------------------------------------
# H5: bulk delete hardening
# --------------------------------------------------------------------------

async def _bulk_ids(client, admin_user, student_user, count=3):
    headers = await auth_headers(client, admin_user)
    resources = [await make_resource(student_user, title=f"Bulk {i}") for i in range(count)]
    return headers, resources


async def test_bulk_delete_dedupes_counts_and_stamps_fields(
    client: AsyncClient, admin_user, student_user
):
    headers, resources = await _bulk_ids(client, admin_user, student_user, 3)
    ids = [str(r.id) for r in resources]
    payload = [ids[0], ids[1], ids[1], ids[2], "nonexistent-id"]

    resp = await client.post("/api/v1/admin/resources/bulk-delete", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted"] == 3, f"duplicates inflated the counter: {body}"
    assert body["failed"] == 1

    for r in resources:
        fresh = await _fetch(Resource, r.id)
        assert fresh.is_deleted is True
        assert fresh.deleted_at is not None
        assert str(fresh.deleted_by_id) == str(admin_user.id)


async def test_bulk_delete_caps_body_size(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    payload = [f"id-{i}" for i in range(101)]

    resp = await client.post("/api/v1/admin/resources/bulk-delete", json=payload, headers=headers)
    assert resp.status_code in (400, 422), f"unbounded body accepted: {resp.status_code}"


async def test_bulk_delete_writes_audit(client: AsyncClient, admin_user, student_user):
    headers, resources = await _bulk_ids(client, admin_user, student_user, 2)
    ids = [str(r.id) for r in resources]

    resp = await client.post("/api/v1/admin/resources/bulk-delete", json=ids, headers=headers)
    assert resp.status_code == 200

    async with _session() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "bulk_delete_resources",
                        AuditLog.actor_id == str(admin_user.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        details = json.loads(rows[0].details_json)
        assert set(ids) <= set(details.get("resource_ids", []))


# --------------------------------------------------------------------------
# M16: single delete stamps deleted_at/deleted_by and writes audit
# --------------------------------------------------------------------------

async def test_single_delete_stamps_fields_and_audits(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user)

    resp = await client.delete(f"/api/v1/admin/resources/{res.id}", headers=headers)
    assert resp.status_code == 200, resp.text

    fresh = await _fetch(Resource, res.id)
    assert fresh.is_deleted is True
    assert fresh.deleted_at is not None
    assert str(fresh.deleted_by_id) == str(admin_user.id)

    async with _session() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "delete_resource",
                        AuditLog.target_id == str(res.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


# --------------------------------------------------------------------------
# M9: course creation audit target_id must be the real id, not "None"
# --------------------------------------------------------------------------

async def test_course_create_audit_has_real_target_id(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    _, course_id = await _make_dept_course(client, headers, "AUD")

    async with _session() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "create_course",
                        AuditLog.target_id == course_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1, "audit target_id was 'None' (written before flush)"


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
