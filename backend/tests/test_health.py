"""Health, root, and public stats endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    # DB exercised: verdict exposed, internals (file sizes, user counts) not
    assert body["database"] == {"status": "healthy"}


@pytest.mark.asyncio
async def test_request_id_echoed_and_generated(client: AsyncClient):
    """X-Request-ID: client-provided safe ids echoed, others generated."""
    r1 = await client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert r1.headers["x-request-id"] == "abc-123"

    r2 = await client.get("/health")
    rid = r2.headers["x-request-id"]
    assert rid and rid != "abc-123" and len(rid) == 32  # uuid4().hex

    # Unsafe incoming id (header-injection / log-forgery attempt) → replaced
    r3 = await client.get("/health", headers={"X-Request-ID": "bad id\nwith-newline"})
    assert "\n" not in r3.headers["x-request-id"]
    assert r3.headers["x-request-id"] != "bad id\nwith-newline"

    # Overlong id → replaced (bounded log lines)
    r4 = await client.get("/health", headers={"X-Request-ID": "x" * 300})
    assert len(r4.headers["x-request-id"]) == 32


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "name" in resp.json()


@pytest.mark.asyncio
async def test_public_stats_shape(client: AsyncClient):
    resp = await client.get("/api/v1/stats")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("resources", "users", "downloads", "courses"):
        assert key in body
