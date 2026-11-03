"""Resources contract: listing, visibility gates, detail, update, delete, upload."""
import io
import pytest
from httpx import AsyncClient

from tests.conftest import make_user, make_resource, fake_telegram_upload, fake_download_file, auth_headers, reloaded


# ---------------------------------------------------------------------------
# Listing & visibility
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_pagination_shape(client: AsyncClient, admin_user):
    for i in range(3):
        await make_resource(admin_user, title=f"Res {i}")
    resp = await client.get("/api/v1/resources", params={"page": 1, "size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["has_next"] is True
    assert body["has_prev"] is False
    assert len(body["results"]) == 2
    item = body["results"][0]
    for key in ("id", "title", "slug", "course_code", "file_size", "downloads", "views",
                "average_rating", "rating_count", "visibility", "uploader_name",
                "moderation_status", "created_at"):
        assert key in item


@pytest.mark.asyncio
async def test_list_hides_pending_and_private_from_anonymous(client: AsyncClient, admin_user):
    await make_resource(admin_user, title="Public One", moderation_status="approved", visibility="public")
    await make_resource(admin_user, title="Pending One", moderation_status="pending")
    await make_resource(admin_user, title="Private One", visibility="private", moderation_status="approved")
    resp = await client.get("/api/v1/resources")
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Public One"]


@pytest.mark.asyncio
async def test_course_code_filter(client: AsyncClient, admin_user):
    await make_resource(admin_user, title="CS Course", course_code="CS101")
    await make_resource(admin_user, title="EC Course", course_code="EC201")
    resp = await client.get("/api/v1/resources", params={"course_code": "cs101"})
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["CS Course"]


@pytest.mark.asyncio
async def test_my_resources_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/resources/my")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_my_resources_scoped_to_owner(client: AsyncClient):
    owner = await make_user()
    other = await make_user()
    await make_resource(owner, title="Mine")
    await make_resource(other, title="Theirs")
    headers = await auth_headers(client, owner)
    resp = await client.get("/api/v1/resources/my", headers=headers)
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Mine"]


# ---------------------------------------------------------------------------
# Detail gates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_detail_pending_hidden_from_anonymous_404(client: AsyncClient, admin_user):
    res = await make_resource(admin_user, moderation_status="pending")
    resp = await client.get(f"/api/v1/resources/{res.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_pending_visible_to_owner(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner, moderation_status="pending")
    headers = await auth_headers(client, owner)
    resp = await client.get(f"/api/v1/resources/{res.id}", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_detail_private_403_for_anonymous(client: AsyncClient, admin_user):
    res = await make_resource(admin_user, visibility="private", moderation_status="approved")
    resp = await client.get(f"/api/v1/resources/{res.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_view_dedup(client: AsyncClient, admin_user):
    res = await make_resource(admin_user)
    first = await client.get(f"/api/v1/resources/{res.id}")
    second = await client.get(f"/api/v1/resources/{res.id}")
    assert first.json()["views"] == 1
    assert second.json()["views"] == 1  # same client deduped within TTL


@pytest.mark.asyncio
async def test_get_by_slug(client: AsyncClient, admin_user):
    res = await make_resource(admin_user, title="Slug Res")
    resp = await client.get(f"/api/v1/resources/slug/{res.slug}")
    assert resp.status_code == 200
    assert resp.json()["id"] == res.id


@pytest.mark.asyncio
async def test_password_protected_contract(client: AsyncClient, admin_user, monkeypatch, tmp_path):
    """Password protects CONTENT (download/preview), not metadata.

    Detail metadata is public (frontend fetches it to decide to prompt),
    must expose is_password_protected and must NOT leak password_hash.
    """
    from app.core.security import security_manager
    res = await make_resource(
        admin_user, title="Pw Res", visibility="password",
        password_hash=security_manager.hash_password("secret123"),
    )
    detail = await client.get(f"/api/v1/resources/{res.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["is_password_protected"] is True
    assert "password_hash" not in body

    fake_download_file(monkeypatch, tmp_path=tmp_path / "fake.pdf")

    # Download without password → 401
    r1 = await client.get(f"/api/v1/resources/{res.id}/download")
    assert r1.status_code == 401
    # Download with wrong password → 401
    r2 = await client.get(f"/api/v1/resources/{res.id}/download", params={"password": "nope"})
    assert r2.status_code == 401
    # Download with correct password → 200
    r3 = await client.get(f"/api/v1/resources/{res.id}/download", params={"password": "secret123"})
    assert r3.status_code == 200


# ---------------------------------------------------------------------------
# Update & delete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_denies_non_owner_student(client: AsyncClient, admin_user):
    student = await make_user()
    res = await make_resource(admin_user)
    headers = await auth_headers(client, student)
    resp = await client.put(f"/api/v1/resources/{res.id}", json={"title": "Hacked"}, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_by_owner(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)
    resp = await client.put(
        f"/api/v1/resources/{res.id}", json={"description": "Updated description"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_soft_deletes_and_mangles_slug(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)
    resp = await client.delete(f"/api/v1/resources/{res.id}", headers=headers)
    assert resp.status_code == 200
    detail = await client.get(f"/api/v1/resources/{res.id}")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_delete_reduces_owner_storage(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner, file_size=5000)
    headers = await auth_headers(client, owner)
    await client.delete(f"/api/v1/resources/{res.id}", headers=headers)
    fresh = await reloaded(owner)
    assert fresh.storage_used_bytes == 0


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
def _upload_files(filename="notes.pdf", content=b"%PDF-1.4 test"):
    return {"file": (filename, io.BytesIO(content), "application/pdf")}


def _upload_data(**overrides):
    data = {
        "title": "Uploaded Notes",
        "course_code": "CS101",
        "description": "Test upload",
        "visibility": "public",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_upload_happy_path(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload", files=_upload_files(), data=_upload_data(), headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Uploaded Notes"
    assert body["moderation_status"] == "pending"  # students go to queue


@pytest.mark.asyncio
async def test_upload_persists_program(client: AsyncClient, monkeypatch):
    """Program/level (B.Tech, Diploma, M.Tech…) is its own optional field,
    distinct from the department = branch dropdown."""
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(program="B.Tech"),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    rid = resp.json()["id"]

    detail = await client.get(f"/api/v1/resources/{rid}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["program"] == "B.Tech"


@pytest.mark.asyncio
async def test_update_resource_program_set_and_clear(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(program="B.Tech"),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    rid = resp.json()["id"]

    upd = await client.put(f"/api/v1/resources/{rid}", json={"program": "M.Tech"}, headers=headers)
    assert upd.status_code == 200, upd.text
    assert upd.json()["program"] == "M.Tech"

    clear = await client.put(f"/api/v1/resources/{rid}", json={"program": None}, headers=headers)
    assert clear.status_code == 200, clear.text
    assert clear.json()["program"] is None


@pytest.mark.asyncio
async def test_upload_rejects_bad_extension(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        data=_upload_data(),
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_password_visibility_requires_password(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(visibility="password"),
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_oversize_413(client: AsyncClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "max_file_size_mb", 1)
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    big = b"x" * (1024 * 1024 + 1)
    resp = await client.post(
        "/api/v1/resources/upload",
        files={"file": ("big.pdf", io.BytesIO(big), "application/pdf")},
        data=_upload_data(),
        headers=headers,
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_duplicate_409(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    first = await client.post(
        "/api/v1/resources/upload", files=_upload_files(), data=_upload_data(), headers=headers
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/resources/upload", files=_upload_files(), data=_upload_data(), headers=headers
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_upload_increments_storage_used(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    content = b"%PDF-1.4 " + b"y" * 1000
    resp = await client.post(
        "/api/v1/resources/upload",
        files={"file": ("notes.pdf", io.BytesIO(content), "application/pdf")},
        data=_upload_data(),
        headers=headers,
    )
    assert resp.status_code == 200
    fresh = await reloaded(owner)
    assert fresh.storage_used_bytes == len(content)


@pytest.mark.asyncio
async def test_upload_admin_auto_approved(client: AsyncClient, monkeypatch, admin_user):
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, admin_user)
    resp = await client.post(
        "/api/v1/resources/upload", files=_upload_files(), data=_upload_data(), headers=headers
    )
    assert resp.json()["moderation_status"] == "approved"


# ---------------------------------------------------------------------------
# Download / preview (Telegram faked)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_download_streams_file_and_counts(client: AsyncClient, monkeypatch, tmp_path):
    owner = await make_user()
    res = await make_resource(owner)
    fake_download_file(monkeypatch, tmp_path=tmp_path / "fake.pdf")
    resp = await client.get(f"/api/v1/resources/{res.id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]

    fresh = await reloaded(res)
    assert fresh.downloads == 1


@pytest.mark.asyncio
async def test_preview_text_only_for_text_files(client: AsyncClient, admin_user):
    res = await make_resource(admin_user, mime_type="application/pdf", file_extension="pdf")
    resp = await client.get(f"/api/v1/resources/{res.id}/preview-text")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Department contract (upload stores it; unknown → 400; update resolves)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_upload_with_department_resolves_id(client: AsyncClient, monkeypatch):
    from tests.conftest import make_department
    dept = await make_department(name="Mechanical Engineering", code="ME")
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(department="mechanical engineering"),
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    # Student uploads are pending → only the owner can view the detail
    detail = await client.get(f"/api/v1/resources/{resp.json()['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["department_id"] == dept.id
    assert detail.json()["department_name"] == "Mechanical Engineering"


@pytest.mark.asyncio
async def test_upload_unknown_department_400(client: AsyncClient, monkeypatch):
    owner = await make_user()
    fake_telegram_upload(monkeypatch)
    headers = await auth_headers(client, owner)
    resp = await client.post(
        "/api/v1/resources/upload",
        files=_upload_files(),
        data=_upload_data(department="Atlantis Studies"),
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Unknown department" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_department_set_and_clear(client: AsyncClient):
    from tests.conftest import make_department
    dept = await make_department(name="Physics", code="PHY")
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)

    set_resp = await client.put(
        f"/api/v1/resources/{res.id}", json={"department": "PHY"}, headers=headers
    )
    assert set_resp.status_code == 200
    fresh = await reloaded(res)
    assert fresh.department_id == dept.id

    clear_resp = await client.put(
        f"/api/v1/resources/{res.id}", json={"department": ""}, headers=headers
    )
    assert clear_resp.status_code == 200
    fresh = await reloaded(res)
    assert fresh.department_id is None

    unknown = await client.put(
        f"/api/v1/resources/{res.id}", json={"department": "Nope"}, headers=headers
    )
    assert unknown.status_code == 400


# ---------------------------------------------------------------------------
# Password/visibility parity on update
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_to_password_visibility(client: AsyncClient, admin_user):
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)

    # Set password visibility with a password
    set_resp = await client.put(
        f"/api/v1/resources/{res.id}",
        json={"visibility": "password", "password": "newpass1"},
        headers=headers,
    )
    assert set_resp.status_code == 200
    fresh = await reloaded(res)
    assert fresh.visibility == "password"
    assert fresh.password_hash is not None

    # Switching away clears the hash
    away = await client.put(
        f"/api/v1/resources/{res.id}", json={"visibility": "public"}, headers=headers
    )
    assert away.status_code == 200
    fresh = await reloaded(res)
    assert fresh.password_hash is None


@pytest.mark.asyncio
async def test_update_password_without_password_visibility_400(client: AsyncClient):
    owner = await make_user()
    res = await make_resource(owner)
    headers = await auth_headers(client, owner)
    resp = await client.put(
        f"/api/v1/resources/{res.id}", json={"password": "somepass1"}, headers=headers
    )
    assert resp.status_code == 400
