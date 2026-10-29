"""Health, root, and public stats endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"


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
