"""Application lifespan: real startup/shutdown wiring, no external services.

The regular test client (ASGITransport) never runs lifespan, so this module
exercises it explicitly against the temp DB: DB init + admin bootstrap,
StatsEngine start/stop, both schedulers, and the Telegram disconnect teardown.
Telegram is the only external dependency faked.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as fastapi_app
from app.services.telegram import telegram_service


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown(monkeypatch):
    stopped = {"disconnected": False}

    async def _fake_connect():
        return False  # credentials are not configured in tests

    async def _fake_disconnect():
        stopped["disconnected"] = True

    monkeypatch.setattr(telegram_service, "connect", _fake_connect)
    monkeypatch.setattr(telegram_service, "disconnect", _fake_disconnect)

    async with fastapi_app.router.lifespan_context(fastapi_app):
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            health = await ac.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "healthy"

    # Shutdown completed and released the Telegram client.
    assert stopped["disconnected"] is True
