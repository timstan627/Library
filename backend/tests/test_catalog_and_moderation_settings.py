"""Admin catalog shelves + runtime settings + upload-moderation matrix.

Covers:
- Public /catalog/shelves (active-only, ordered; empty until configured).
- Admin shelf CRUD /authz (create validation, update, toggle, move, delete).
- Global moderation setting (default off, toggle persists, admin-only).
- Upload auto-approve decision matrix (global toggle, per-user exemption).
- Per-user moderation-exempt toggle guards (self/admin targets, unknown).
"""
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, auth_headers, fake_telegram_upload

from tests.test_resources import _upload_files, _upload_data

SHELF = {
    "title": "Fresh Uploads",
    "source_type": "recent",
    "item_limit": 10,
}


async def _mk_shelf(
    client: AsyncClient, headers: dict, **overrides
) -> dict:
    payload = {**SHELF, **overrides}
    resp = await client.post("/api/v1/admin/catalog/shelves", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Public shelves
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_shelves_empty_by_default(client: AsyncClient):
    resp = await client.get("/api/v1/catalog/shelves")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_public_shelves_active_only_and_ordered(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    a = await _mk_shelf(client, headers, title="Row A")
    b = await _mk_shelf(client, headers, title="Row B")
    hidden = await _mk_shelf(client, headers, title="Hidden", source_type="most_read")
    tog = await client.patch(f"/api/v1/admin/catalog/shelves/{hidden['id']}/toggle", headers=headers)
    assert tog.status_code == 200
    # Row A flipped inactive too — only Row B remains public.
    await client.patch(
        f"/api/v1/admin/catalog/shelves/{a['id']}/toggle", headers=headers
    )

    resp = await client.get("/api/v1/catalog/shelves")
    assert resp.status_code == 200
    rows = resp.json()
    assert [r["title"] for r in rows] == ["Row B"]
    assert rows[0]["id"] == b["id"]
    # Public payload strips admin-only fields.
    for key in ("position", "is_active"):
        assert key not in rows[0]


# ---------------------------------------------------------------------------
# Admin shelf CRUD
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_shelf_admin_only(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/admin/catalog/shelves", json=SHELF)
    assert resp.status_code in (401, 403)
    headers = await auth_headers(client, await make_user())
    resp = await client.post("/api/v1/admin/catalog/shelves", json=SHELF, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_shelf_create_value_validation(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    resp = await client.post(
        "/api/v1/admin/catalog/shelves",
        json={**SHELF, "source_type": "tag", "source_value": None},
        headers=headers,
    )
    assert resp.status_code == 400
    tag = await _mk_shelf(client, headers, title="Tag Row", source_type="tag", source_value="system-design")
    assert tag["source_value"] == "system-design"
    # Built-in types ignore/null the value even if a client sends one.
    row = await _mk_shelf(client, headers, title="Rec Row", source_type="most_read", source_value="junk")
    assert row["source_value"] is None


@pytest.mark.asyncio
async def test_shelf_create_appends_position(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    first = await _mk_shelf(client, headers, title="First")
    second = await _mk_shelf(client, headers, title="Second")
    assert second["position"] == first["position"] + 1


@pytest.mark.asyncio
async def test_shelf_update_toggle_delete(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    shelf = await _mk_shelf(client, headers)

    upd = await client.put(
        f"/api/v1/admin/catalog/shelves/{shelf['id']}",
        json={"title": "Renamed", "source_type": "subject", "source_value": "CS Dept", "item_limit": 5, "position": shelf["position"], "is_active": True},
        headers=headers,
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["title"] == "Renamed"
    assert upd.json()["source_value"] == "CS Dept"

    tog = await client.patch(f"/api/v1/admin/catalog/shelves/{shelf['id']}/toggle", headers=headers)
    assert tog.status_code == 200
    assert tog.json()["is_active"] is False

    gone = await client.delete(f"/api/v1/admin/catalog/shelves/{shelf['id']}", headers=headers)
    assert gone.status_code == 204
    missing = await client.get(f"/api/v1/admin/catalog/shelves/{shelf['id']}", headers=headers)
    assert missing.status_code in (404, 405)


@pytest.mark.asyncio
async def test_shelf_move_up_down(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    a = await _mk_shelf(client, headers, title="A")
    b = await _mk_shelf(client, headers, title="B")
    c = await _mk_shelf(client, headers, title="C")

    moved = await client.patch(f"/api/v1/admin/catalog/shelves/{c['id']}/move", json={"direction": "up"}, headers=headers)
    assert moved.status_code == 200, moved.text
    assert [r["title"] for r in moved.json()] == ["A", "C", "B"]

    moved = await client.patch(f"/api/v1/admin/catalog/shelves/{c['id']}/move", json={"direction": "up"}, headers=headers)
    assert [r["title"] for r in moved.json()] == ["C", "A", "B"]

    moved = await client.patch(f"/api/v1/admin/catalog/shelves/{c['id']}/move", json={"direction": "down"}, headers=headers)
    assert [r["title"] for r in moved.json()] == ["A", "C", "B"]

    # Moving the bottom-most shelf down is a no-op.
    moved = await client.patch(f"/api/v1/admin/catalog/shelves/{b['id']}/move", json={"direction": "down"}, headers=headers)
    assert moved.status_code == 200
    assert [r["title"] for r in moved.json()] == ["A", "C", "B"]


@pytest.mark.asyncio
async def test_shelf_unknown_id_404(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    resp = await client.put(
        "/api/v1/admin/catalog/shelves/nope",
        json={"title": "x", "source_type": "recent", "item_limit": 3, "position": 0, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 404
    resp = await client.delete("/api/v1/admin/catalog/shelves/nope", headers=headers)
    assert resp.status_code == 404
    resp = await client.patch("/api/v1/admin/catalog/shelves/nope/toggle", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Global moderation setting
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_moderation_setting_defaults_and_persists(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    resp = await client.get("/api/v1/admin/settings/moderation", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["auto_approve_moderation"] is False

    resp = await client.patch(
        "/api/v1/admin/settings/moderation",
        json={"auto_approve_moderation": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["auto_approve_moderation"] is True

    fresh = await client.get("/api/v1/admin/settings/moderation", headers=headers)
    assert fresh.json()["auto_approve_moderation"] is True


@pytest.mark.asyncio
async def test_moderation_setting_admin_only(client: AsyncClient, admin_user):
    resp = await client.get("/api/v1/admin/settings/moderation")
    assert resp.status_code in (401, 403)
    headers = await auth_headers(client, await make_user())
    resp = await client.get("/api/v1/admin/settings/moderation", headers=headers)
    assert resp.status_code == 403
    resp = await client.patch(
        "/api/v1/admin/settings/moderation",
        json={"auto_approve_moderation": True},
        headers=headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Upload moderation decision matrix
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_upload_pending_when_moderation_default(client: AsyncClient, admin_user, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moderation_status"] == "pending"


@pytest.mark.asyncio
async def test_upload_auto_approved_when_global_toggle_on(client: AsyncClient, admin_user, monkeypatch):
    headers = await auth_headers(client, admin_user)
    resp = await client.patch(
        "/api/v1/admin/settings/moderation",
        json={"auto_approve_moderation": True},
        headers=headers,
    )
    assert resp.status_code == 200

    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    user_headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moderation_status"] == "approved"


@pytest.mark.asyncio
async def test_upload_auto_approved_for_exempt_user(client: AsyncClient, admin_user, monkeypatch):
    owner = await make_user()
    headers = await auth_headers(client, admin_user)
    resp = await client.patch(
        f"/api/v1/admin/users/{owner.id}/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    fake_telegram_upload(monkeypatch)
    user_headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moderation_status"] == "approved"


@pytest.mark.asyncio
async def test_admin_upload_always_approved_even_with_moderation_on(client: AsyncClient, admin_user, monkeypatch):
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, admin_user)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moderation_status"] == "approved"


# ---------------------------------------------------------------------------
# Per-user moderation exemption endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_moderation_exempt_toggle_and_listing(client: AsyncClient, admin_user):
    target = await make_user()
    headers = await auth_headers(client, admin_user)
    resp = await client.patch(
        f"/api/v1/admin/users/{target.id}/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    listing = await client.get("/api/v1/admin/users", headers=headers)
    assert listing.status_code == 200
    row = next(u for u in listing.json()["results"] if u["id"] == target.id)
    assert row["moderation_exempt"] is True


@pytest.mark.asyncio
async def test_moderation_exempt_guards(client: AsyncClient, admin_user):
    headers = await auth_headers(client, admin_user)
    resp = await client.patch(
        f"/api/v1/admin/users/{admin_user.id}/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 400

    mod = await make_user(role="moderator")
    resp = await client.patch(
        f"/api/v1/admin/users/{mod.id}/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 400

    resp = await client.patch(
        "/api/v1/admin/users/does-not-exist/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_moderation_exempt_admin_only(client: AsyncClient, admin_user):
    target = await make_user()
    resp = await client.patch(
        f"/api/v1/admin/users/{target.id}/moderation-exempt",
        json={"moderation_exempt": True},
    )
    assert resp.status_code in (401, 403)
    headers = await auth_headers(client, await make_user())
    resp = await client.patch(
        f"/api/v1/admin/users/{target.id}/moderation-exempt",
        json={"moderation_exempt": True},
        headers=headers,
    )
    assert resp.status_code == 403
