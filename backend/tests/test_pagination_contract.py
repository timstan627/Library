"""Iteration-3 pagination contract tests: M15.

Every admin paginated endpoint must return the same envelope:
    {results, total, page, page_size, pages}
with pages = ceil(total / page_size) — i.e. 0 when the list is empty.

Red-first: tests below fail against the pre-unification code, which mixes
bare lists (history, trusted), missing keys (pending, users, audit-logs,
departments, courses, ratings), and an outlier pages=1-when-empty (reports).
"""
from httpx import AsyncClient

from app.models.resource import Resource
from tests.conftest import make_resource, auth_headers


def _assert_envelope(body: dict, page: int = 1, page_size: int = 20, total: int | None = None):
    for key in ("results", "total", "page", "page_size", "pages"):
        assert key in body, f"envelope missing '{key}': {list(body.keys())}"
    assert body["page"] == page
    assert body["page_size"] == page_size
    if total is not None:
        assert body["total"] == total
    assert body["pages"] == (total + page_size - 1) // page_size if total is not None else True


async def test_reports_pages_zero_when_empty(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/reports?report_status=pending&page=1&page_size=20",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    if body["total"] == 0:
        assert body["pages"] == 0, (
            f"empty reports list must have pages=0, got {body['pages']}"
        )


async def test_moderation_pending_full_envelope(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    await make_resource(student_user, moderation_status="pending")

    resp = await client.get(
        "/api/v1/admin/moderation/pending?page=1&page_size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["results"], list) and len(body["results"]) >= 1
    _assert_envelope(body, page=1, page_size=20)


async def test_moderation_history_envelope(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user, moderation_status="pending")
    await client.post(
        f"/api/v1/admin/moderation/{res.id}/moderate",
        json={"action": "approve"},
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/admin/moderation/history?page=1&page_size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict), (
        f"/history returned a bare list; expected envelope: {type(body).__name__}"
    )
    assert isinstance(body["results"], list) and len(body["results"]) >= 1
    _assert_envelope(body, page=1, page_size=20)


async def test_admin_users_full_envelope(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/users?page=1&page_size=50", headers=headers
    )
    assert resp.status_code == 200
    _assert_envelope(resp.json(), page=1, page_size=50)


async def test_admin_trusted_users_envelope(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/users/trusted?page=1&page_size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict), (
        f"/trusted returned a bare list; expected envelope: {type(body).__name__}"
    )
    _assert_envelope(body, page=1, page_size=20)


async def test_admin_departments_include_pages(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/departments?page=1&page_size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "pages" in body, f"departments envelope missing 'pages': {list(body.keys())}"
    assert body["pages"] == (body["total"] + 20 - 1) // 20


async def test_admin_courses_include_pages(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/courses?page=1&page_size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "pages" in body, f"courses envelope missing 'pages': {list(body.keys())}"
    assert body["pages"] == (body["total"] + 20 - 1) // 20


async def test_audit_logs_include_page_size(
    client: AsyncClient, admin_user
):
    headers = await auth_headers(client, admin_user)
    resp = await client.get(
        "/api/v1/admin/moderation/audit-logs?page=1&page_size=50", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_size"] == 50, f"audit-logs envelope missing page_size: {body.keys()}"
    assert body["pages"] == (body["total"] + 50 - 1) // 50


async def test_ratings_include_page_size(
    client: AsyncClient, admin_user, student_user
):
    headers = await auth_headers(client, admin_user)
    res = await make_resource(student_user)
    resp = await client.get(
        f"/api/v1/ratings/resources/{res.id}?page=1&size=20", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_size"] == 20, f"ratings envelope missing page_size: {body.keys()}"
