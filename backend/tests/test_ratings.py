"""Ratings contract: create/update/delete, aggregates, self-rating guard."""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, auth_headers, reloaded


@pytest.mark.asyncio
async def test_create_rating_updates_aggregates(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, rater)

    resp = await client.post(
        f"/api/v1/ratings/resources/{res.id}", json={"value": 5, "review": "Great"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["value"] == 5
    assert body["user_name"] == rater.display_name
    assert "password_hash" not in body

    fresh = await reloaded(res)
    assert fresh.rating_sum == 5
    assert fresh.rating_count == 1


@pytest.mark.asyncio
async def test_rating_unapproved_resource_404(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner, moderation_status="pending")
    headers = await auth_headers(client, rater)
    resp = await client.post(
        f"/api/v1/ratings/resources/{res.id}", json={"value": 4}, headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_rate_own_resource(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        f"/api/v1/ratings/resources/{res.id}", json={"value": 5}, headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_rating_requires_auth(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner)
    resp = await client.post(f"/api/v1/ratings/resources/{res.id}", json={"value": 5})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_rating_single_row_and_aggregates(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, rater)

    first = await client.post(f"/api/v1/ratings/resources/{res.id}", json={"value": 5}, headers=headers)
    assert first.status_code == 200
    second = await client.post(f"/api/v1/ratings/resources/{res.id}", json={"value": 2}, headers=headers)
    assert second.status_code == 200

    fresh = await reloaded(res)
    assert fresh.rating_sum == 2  # 5 replaced by 2, not added
    assert fresh.rating_count == 1  # still one rating row

    listing = await client.get(f"/api/v1/ratings/resources/{res.id}")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["rating_count"] == 1
    assert body["average_rating"] == 2.0


@pytest.mark.asyncio
async def test_review_only_rating_does_not_count(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, rater)

    resp = await client.post(
        f"/api/v1/ratings/resources/{res.id}", json={"value": 0, "review": "Just a comment"}, headers=headers
    )
    assert resp.status_code == 200
    fresh = await reloaded(res)
    assert fresh.rating_sum == 0
    assert fresh.rating_count == 0


@pytest.mark.asyncio
async def test_delete_rating_decrements_aggregates(client: AsyncClient):
    owner = await make_user()
    rater = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, rater)
    await client.post(f"/api/v1/ratings/resources/{res.id}", json={"value": 4}, headers=headers)

    deleted = await client.delete(f"/api/v1/ratings/resources/{res.id}", headers=headers)
    assert deleted.status_code == 200

    fresh = await reloaded(res)
    assert fresh.rating_sum == 0
    assert fresh.rating_count == 0

    again = await client.delete(f"/api/v1/ratings/resources/{res.id}", headers=headers)
    assert again.status_code == 404
