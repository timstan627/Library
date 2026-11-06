"""Regression tests for the FastAPI review fixes.

Covers:
- missing credentials → 401 (RFC 9110), not the HTTPBearer-default 403
- private resources gate their ratings endpoints like the resource endpoints
- the multipart upload path enforces the same field rules as the schemas
"""
import io
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, auth_headers, fake_telegram_upload


@pytest.mark.asyncio
async def test_missing_credentials_return_401(client: AsyncClient):
    resp = await client.get("/api/v1/resources/my")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_private_resource_ratings_hidden_from_non_owners(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner, visibility="private", moderation_status="approved")

    # Anonymous reader → 403 (private), matching the resource detail endpoint.
    anon = await client.get(f"/api/v1/ratings/resources/{res.id}")
    assert anon.status_code == 403

    headers = await auth_headers(client, rater)
    listing = await client.get(f"/api/v1/ratings/resources/{res.id}", headers=headers)
    assert listing.status_code == 403

    blocked = await client.post(
        f"/api/v1/ratings/resources/{res.id}", json={"value": 5}, headers=headers
    )
    assert blocked.status_code == 403

    # The owner still sees their own private resource's ratings.
    owner_headers = await auth_headers(client, owner)
    mine = await client.get(f"/api/v1/ratings/resources/{res.id}", headers=owner_headers)
    assert mine.status_code == 200


@pytest.mark.asyncio
async def test_upload_enforces_create_schema_rules(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)

    def files():
        return {"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}

    # Course code that the JSON update path would reject → 400 here too.
    bad_code = await client.post(
        "/api/v1/resources/upload",
        files=files(),
        data={"title": "Bad Course", "course_code": "AB", "visibility": "public"},
        headers=headers,
    )
    assert bad_code.status_code == 400

    # Title shorter than the schema minimum → rejected by Form validation.
    short_title = await client.post(
        "/api/v1/resources/upload",
        files=files(),
        data={"title": "ab", "course_code": "CS101", "visibility": "public"},
        headers=headers,
    )
    assert short_title.status_code == 422

    # Valid lowercase code is normalized exactly like the schema validators.
    ok = await client.post(
        "/api/v1/resources/upload",
        files=files(),
        data={"title": "Good Course", "course_code": "cs101", "visibility": "public"},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    detail = await client.get(f"/api/v1/resources/{ok.json()['id']}", headers=headers)
    assert detail.json()["course_code"] == "CS101"
