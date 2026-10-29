"""Search contract: filters, sorting, popular/recent, and ORM-leak guard."""
import pytest
from httpx import AsyncClient
from sqlalchemy import update

from tests.conftest import make_user, make_resource
from app.core.database import async_session


@pytest.mark.asyncio
async def test_search_pagination_shape(client: AsyncClient, admin_user):
    for i in range(3):
        await make_resource(admin_user, title=f"Searchable {i}")
    resp = await client.get("/api/v1/search", params={"q": "searchable", "size": 2})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("results", "total", "page", "pages", "took_ms", "query"):
        assert key in body
    assert body["total"] == 3
    assert body["query"] == "searchable"


@pytest.mark.asyncio
async def test_search_only_public_approved(client: AsyncClient, admin_user):
    await make_resource(admin_user, title="Visible Doc")
    await make_resource(admin_user, title="Pending Doc", moderation_status="pending")
    await make_resource(admin_user, title="Private Doc", visibility="private", moderation_status="approved")
    await make_resource(admin_user, title="Unlisted Doc", visibility="unlisted", moderation_status="approved")
    await make_resource(admin_user, title="Deleted Doc", is_deleted=True)
    resp = await client.get("/api/v1/search", params={"q": "doc"})
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Visible Doc"]


@pytest.mark.asyncio
async def test_search_matches_tags_and_course_code(client: AsyncClient, admin_user):
    await make_resource(admin_user, title="DSA Notes", tags=["algorithms", "trees"])
    await make_resource(admin_user, title="Other Notes", course_code="CS999")
    by_tag = await client.get("/api/v1/search", params={"q": "algorithms"})
    assert [r["title"] for r in by_tag.json()["results"]] == ["DSA Notes"]
    by_code = await client.get("/api/v1/search", params={"q": "CS999"})
    assert [r["title"] for r in by_code.json()["results"]] == ["Other Notes"]


@pytest.mark.asyncio
async def test_search_sort_by_downloads(client: AsyncClient, admin_user):
    a = await make_resource(admin_user, title="Few Downloads")
    b = await make_resource(admin_user, title="Many Downloads")
    async with async_session() as session:
        for res, count in ((a, 2), (b, 10)):
            await session.execute(
                update(type(res)).where(type(res).id == res.id).values(downloads=count)
            )
        await session.commit()
    resp = await client.get("/api/v1/search", params={"q": "downloads", "sort_by": "downloads"})
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Many Downloads", "Few Downloads"]


@pytest.mark.asyncio
async def test_search_no_results_is_200(client: AsyncClient, admin_user):
    resp = await client.get("/api/v1/search", params={"q": "zzz-no-match-zzz"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_filters_returns_options(client: AsyncClient, admin_user):
    await make_resource(admin_user, title="A", course_code="CS101", semester="3", branch="CSE")
    resp = await client.get("/api/v1/search/filters")
    assert resp.status_code == 200
    body = resp.json()
    assert "CS101" in body["courses"]
    assert "3" in body["semesters"]
    assert "CSE" in body["branches"]


@pytest.mark.asyncio
async def test_popular_orders_by_downloads_and_respects_limit(client: AsyncClient, admin_user):
    made = [await make_resource(admin_user, title=f"Pop {i}") for i in range(3)]
    async with async_session() as session:
        for res, count in zip(made, (1, 10, 5)):
            await session.execute(update(type(res)).where(type(res).id == res.id).values(downloads=count))
        await session.commit()
    resp = await client.get("/api/v1/search/popular", params={"limit": 2})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[0]["downloads"] == 10


@pytest.mark.asyncio
async def test_recent_orders_by_created(client: AsyncClient, admin_user):
    first = await make_resource(admin_user, title="Older")
    second = await make_resource(admin_user, title="Newer")
    resp = await client.get("/api/v1/search/recent", params={"limit": 1})
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["title"] == "Newer"


# ---------------------------------------------------------------------------
# SECURITY regression guard: popular/recent must return safe summaries,
# not raw ORM rows (leaks password_hash, uploader email/mfa_secret,
# telegram file ids, file_hash). Fixed by Task 1.1; strict xfail ratchets.
# ---------------------------------------------------------------------------
FORBIDDEN_KEYS = {
    "password_hash", "file_hash", "telegram_file_id", "telegram_message_id",
    "telegram_channel_id", "moderated_by_id", "deleted_by_id", "uploader",
    "mfa_secret", "email",
}


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="SECURITY: /search/popular serializes raw ORM rows (Task 1.1)")
async def test_popular_no_orm_leak(client: AsyncClient):
    uploader = await make_user(email="leakpop@test.example", password="Sup3rSecret!")
    await make_resource(uploader, title="Leak Check Pop")
    resp = await client.get("/api/v1/search/popular")
    item = resp.json()["results"][0]
    leaked = FORBIDDEN_KEYS & set(item.keys())
    assert not leaked, f"popular leaks internal fields: {leaked}"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="SECURITY: /search/recent serializes raw ORM rows (Task 1.1)")
async def test_recent_no_orm_leak(client: AsyncClient):
    uploader = await make_user(email="leakrecent@test.example", password="Sup3rSecret!")
    await make_resource(uploader, title="Leak Check Recent")
    resp = await client.get("/api/v1/search/recent")
    item = resp.json()["results"][0]
    leaked = FORBIDDEN_KEYS & set(item.keys())
    assert not leaked, f"recent leaks internal fields: {leaked}"
