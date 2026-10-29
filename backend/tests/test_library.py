"""Library (collections) contract: CRUD, items, ownership isolation."""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, auth_headers


async def create_collection(client, headers, name="My Collection", **extra):
    resp = await client.post(
        "/api/v1/library/collections", json={"name": name, **extra}, headers=headers
    )
    return resp


@pytest.mark.asyncio
async def test_collection_crud_flow(client: AsyncClient):
    user = await make_user()
    headers = await auth_headers(client, user)

    created = await create_collection(client, headers, name="Exam Prep")
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Exam Prep"
    assert body["item_count"] == 0
    collection_id = body["id"]

    listed = await client.get("/api/v1/library/collections", headers=headers)
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [collection_id]

    detail = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["items"] == []

    updated = await client.put(
        f"/api/v1/library/collections/{collection_id}",
        json={"name": "Renamed", "description": "Updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"

    deleted = await client.delete(f"/api/v1/library/collections/{collection_id}", headers=headers)
    assert deleted.status_code == 200
    gone = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_collection_isolated_between_users(client: AsyncClient):
    owner = await make_user()
    stranger = await make_user()
    headers = await auth_headers(client, owner)
    created = await create_collection(client, headers)
    collection_id = created.json()["id"]

    stranger_headers = await auth_headers(client, stranger)
    resp = await client.get(f"/api/v1/library/collections/{collection_id}", headers=stranger_headers)
    assert resp.status_code == 404
    resp = await client.put(
        f"/api/v1/library/collections/{collection_id}", json={"name": "Hijacked"}, headers=stranger_headers
    )
    assert resp.status_code in (403, 404)
    resp = await client.delete(f"/api/v1/library/collections/{collection_id}", headers=stranger_headers)
    assert resp.status_code in (403, 404)
    resp = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": ["some-resource-id"]},
        headers=stranger_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_items_own_resources_only(client: AsyncClient):
    owner = await make_user()
    other = await make_user()
    mine = await make_resource(owner, title="Mine")
    theirs = await make_resource(other, title="Theirs")
    headers = await auth_headers(client, owner)
    collection_id = (await create_collection(client, headers)).json()["id"]

    resp = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [mine.id, theirs.id]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 1
    assert body["skipped"] == 1  # someone else's resource is silently skipped

    detail = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    items = detail.json()["items"]
    assert [i["resource_id"] for i in items] == [mine.id]
    assert items[0]["title"] == "Mine"

    # Duplicate add is idempotent
    dup = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [mine.id]},
        headers=headers,
    )
    assert dup.json()["added"] == 0


@pytest.mark.asyncio
async def test_remove_item_and_reorder(client: AsyncClient):
    owner = await make_user()
    r1 = await make_resource(owner, title="First")
    r2 = await make_resource(owner, title="Second")
    r3 = await make_resource(owner, title="Third")
    headers = await auth_headers(client, owner)
    collection_id = (await create_collection(client, headers)).json()["id"]
    await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [r1.id, r2.id, r3.id]},
        headers=headers,
    )

    reorder = await client.put(
        f"/api/v1/library/collections/{collection_id}/reorder",
        json={"resource_ids": [r3.id, r1.id, r2.id]},
        headers=headers,
    )
    assert reorder.status_code == 200

    detail = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    order = [i["resource_id"] for i in detail.json()["items"]]
    assert order == [r3.id, r1.id, r2.id]

    removed = await client.delete(
        f"/api/v1/library/collections/{collection_id}/items/{r1.id}", headers=headers
    )
    assert removed.status_code == 200
    detail = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    assert [i["resource_id"] for i in detail.json()["items"]] == [r3.id, r2.id]


@pytest.mark.asyncio
async def test_remove_item_no_ownership_oracle(client: AsyncClient):
    """A stranger probing DELETE must see 404 whether or not the item exists.

    Check-item-then-ownership answered 403 for existing items in other
    people's collections — an existence oracle. Both cases now return 404.
    """
    owner = await make_user()
    stranger = await make_user()
    r1 = await make_resource(owner, title="Owned Item")
    headers = await auth_headers(client, owner)
    collection_id = (await create_collection(client, headers)).json()["id"]
    await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [r1.id]},
        headers=headers,
    )

    stranger_headers = await auth_headers(client, stranger)
    # Item exists but belongs to someone else's collection → 404 (not 403)
    leak = await client.delete(
        f"/api/v1/library/collections/{collection_id}/items/{r1.id}",
        headers=stranger_headers,
    )
    assert leak.status_code == 404
    # Same status for a nonexistent item → indistinguishable
    missing = await client.delete(
        f"/api/v1/library/collections/{collection_id}/items/00000000-0000-0000-0000-000000000000",
        headers=stranger_headers,
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_add_items_request_size_and_recent_limit_bounds(client: AsyncClient):
    owner = await make_user()
    headers = await auth_headers(client, owner)
    collection_id = (await create_collection(client, headers)).json()["id"]

    # resource_ids beyond the 100-item request cap → 422
    big = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [f"id-{i}" for i in range(101)]},
        headers=headers,
    )
    assert big.status_code == 422

    # Empty add request is a validation error, not a silent no-op
    empty = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": []},
        headers=headers,
    )
    assert empty.status_code == 422

    # /recent: limit must be within 1..50 (negative LIMIT = unlimited in SQLite)
    for bad in (0, -1, 51):
        resp = await client.get("/api/v1/library/recent", params={"limit": bad}, headers=headers)
        assert resp.status_code == 422, f"limit={bad} → {resp.status_code}"
    ok = await client.get("/api/v1/library/recent", params={"limit": 50}, headers=headers)
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_add_items_batch_counts(client: AsyncClient):
    """Mixed validity in one request: owned added, foreign/unknown skipped."""
    owner = await make_user()
    other = await make_user()
    mine1 = await make_resource(owner, title="M1")
    mine2 = await make_resource(owner, title="M2")
    theirs = await make_resource(other, title="T")
    headers = await auth_headers(client, owner)
    collection_id = (await create_collection(client, headers)).json()["id"]

    resp = await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [mine1.id, theirs.id, "nonexistent-id", mine2.id]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 2
    assert body["skipped"] == 2

    detail = await client.get(f"/api/v1/library/collections/{collection_id}", headers=headers)
    order = [i["resource_id"] for i in detail.json()["items"]]
    assert order == [mine1.id, mine2.id]  # request order preserved


@pytest.mark.asyncio
async def test_recent_and_uncategorized_count(client: AsyncClient):
    owner = await make_user()
    r1 = await make_resource(owner, title="Recent One")
    await make_resource(owner, title="Recent Two")
    headers = await auth_headers(client, owner)

    recent = await client.get("/api/v1/library/recent", params={"limit": 1}, headers=headers)
    assert recent.status_code == 200
    body = recent.json()
    assert len(body) == 1
    assert body[0]["title"] == "Recent Two"

    uncategorized = await client.get("/api/v1/library/uncategorized-count", headers=headers)
    assert uncategorized.status_code == 200
    assert uncategorized.json()["uncategorized"] == 2

    # Put one into a collection → count drops
    collection_id = (await create_collection(client, headers)).json()["id"]
    await client.post(
        f"/api/v1/library/collections/{collection_id}/items",
        json={"resource_ids": [r1.id]},
        headers=headers,
    )
    uncategorized = await client.get("/api/v1/library/uncategorized-count", headers=headers)
    assert uncategorized.json()["uncategorized"] == 1
