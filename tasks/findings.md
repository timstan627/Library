# Backend Audit Findings (merged, verified)

Merged from two line-by-line audits (routers + support files) plus the primary
audit of core files. Every finding below was verified against source or a live
response. Statuses update as phases complete.

## Critical

| # | Location | Finding | Status |
|---|----------|---------|--------|
| C1 | `api/v1/search.py` `/popular`, `/recent` | Return raw ORM `Resource` rows (verified live): leaks `uploader.password_hash`, `email`, `mfa_secret`, `telegram_file_id/channel_id`, `file_hash` | open → Task 1.1 |
| C2 | `alembic/env.py:13` | `from app.models.base import Base` — Base is not there → **all migrations crash on import** | open → Task 4.x |
| C3 | `alembic/versions/001_initial.py` | Migration targets PostgreSQL (UUID/ARRAY/JSONB/TSVECTOR/`uuid_generate_v4`) while the app runs SQLite; alembic not even in requirements | open → Task 4.x |
| C4 | `scripts/check_courses.py`, `clear_resources.py` | Hardcoded live MongoDB Atlas credentials in repo; `clear_resources.py` wipes a remote DB unconditionally | open → delete scripts + rotate creds |
| C5 | `Dockerfile:15` | `COPY . .` with no `.dockerignore` → bakes `.env`, live SQLite DBs, `venv/` into image layers | open → Task 4.3 |
| C6 | `models/rating.py` | No UNIQUE constraint on (user_id, resource_id) → concurrent double-rating double-counts aggregates | open → Task 1.4 |

## High

| # | Location | Finding | Status |
|---|----------|---------|--------|
| H1 | `tasks/scheduled_backup.py:44` | Backup upload reads the **live** DB file, not the validated snapshot it just created (`backup_result["path"]` unused) → torn/WAL-inconsistent Telegram backups | open → Task 1.3 |
| H2 | `admin/courses.py:183`, `admin/departments.py:150-156` | Delete cascades **hard-delete every resource row** (bypasses soft-delete, orphans Telegram files, audit omits counts) | open |
| H3 | `api/v1/courses.py:59-61` | Public endpoint `detail=str(e)` — leaks internal error text | open |
| H4 | `admin/users.py:55-60` | N+1: up to 400 sequential count queries per list request | open |
| H5 | `admin/resources.py:89-113` | Bulk delete: unbounded body, N sequential SELECTs, bare `except`, duplicates inflate counter, no audit | open |
| H6 | `core/database.py` | `PRAGMA foreign_keys=ON` set once on one pooled connection, not per-connection; no busy_timeout → FK effectively off + "database is locked" risk | open → Task 1.2 |
| H7 | `tasks/cleanup.py`, `tasks/analytics.py` | Nothing schedules them; sessions accumulate forever, soft-deleted resources never purge; `cleanup` hard-DELETEs resources that have child FK rows → IntegrityError swallowed | open |
| H8 | `models/user.py` | `User.resources`/`User.sessions` `lazy="selectin"` → every auth request eager-loads the user's entire resource list + all sessions | open → Task 3.2 |
| H9 | `.github/workflows/ci.yml` | Fictional CI: Postgres+Redis services (unused), refs missing `Dockerfile.prod`/`docker-compose.prod.yml`, runs nonexistent pytest suite | open → Task 4.2 |
| H10 | `scripts/*` + root scripts | 12 dead Mongo/Beanie scripts (unrunnable); `reset_password*.py`/`promote_admin.py` contain real user emails + a real password | open → delete + rotate |

## Medium

| # | Location | Finding | Status |
|---|----------|---------|--------|
| M1 | `api/v1/search.py` | Exception swallow → 200 with empty results on DB failure; LIKE wildcards unescaped; `sort_by=rating` sorts by sum not average; `department` accepted and dropped | open → Task 2.1/2.2 |
| M2 | `search.py /filters` | `departments=[]` hardcoded; courses leak from non-approved resources (no moderation filter) | open → Task 2.1 |
| M3 | `api/v1/resources.py` | Upload accepts `department`, never stores `department_id`; `ResourceResponse.department: Optional[str]` vs ORM relationship → latent 500 once any resource gets a department | open → Task 2.1 |
| M4 | `library.py` | `remove_item` checks item before ownership (404/403 oracle); `add_items` N+1 per id; negative `limit` unclamped; uncategorized count includes other users' items in joins? (verified: scoped by Collection.user_id — ok) | open → Task 2.4 |
| M5 | `admin/moderation.py` | Can moderate soft-deleted pending resource (state pollution); check-then-act race between moderators; `/history` + admin `/trusted` paginate with bare lists (unpageable) | open |
| M6 | `admin/reports.py:93` | Resolving an already-resolved report silently overwrites resolver + note | open |
| M7 | `password_reset.py` | Token store unbounded + multiple concurrent valid tokens per user + no sweep; reset path skips password-complexity (duplicated schema); token consumption not atomic (pop-first fix); request checks is_active but confirm doesn't; no rate limit/audit | open → Task 2.3 |
| M8 | `auth.py` | Register check-then-insert race → 500 (IntegrityError uncaught); slug collision → 409 instead of retry | open → Task 1.6 |
| M9 | `admin/courses.py:99` | Audit log written **before** flush → `target_id="None"` for every course creation | open |
| M10 | `email.py` | No SMTP timeout (hangs background thread); socket leak on failure (no try/finally); failures swallowed | open |
| M11 | `download_manager.py` | Blocking `shutil.copy2`/stat/open in async paths; temp-file leak when file > cache threshold; `_stream_from_disk` fake-async | open → Task 3.3 |
| M12 | `services/telegram.py` | `/dbinit` handler NameError (`Path` not imported); fire-and-forget backup task never referenced (GC risk); backup message ids never persisted | open → Task 1.7/3.4 |
| M13 | `services/cache.py` | `_lock` declared never used; thundering-herd duplicate refetch; entire 500MB in-memory FileCache is dead code | open → Task 3.4 |
| M14 | requirements.txt | `redis`, `python-magic`, `sentry-sdk` unused (grep-verified); dev deps ship in prod image; `alembic` missing | open → Task 4.2 |
| M15 | Cross-router | Pagination envelope differs 6 ways; `pages` semantics differ when empty (0 vs 1); audit-log failure policy inconsistent (swallow vs fail); role vocabulary `student` vs `user` | open → Task 2.5 |
| M16 | `admin/resources.py` | Single delete: no audit, `deleted_at/deleted_by_id` never populated anywhere | open |
| M17 | `public courses.py`/`departments.py` | Detail endpoints serve deactivated (`is_active=False`) rows — list/detail disagree | open |

## Low / Nit (fix opportunistically)

- `TokenResponse.expires_in` default 900 vs config 3600; `traceback.print_exc()` in upload path
- `cache.py` declared `_lock` unused; `semaphore._value` private access
- `schemas/rating.py` uuid.UUID vs str ids; `schemas/__init__.py` missing exports; `ModerationAction.action` should be Literal
- `Collection.emoji` mojibake default (`dY"?`)
- Root dev scripts (`debug_db.py`, `fix_admin.py`, `inspect_*.py`, `seed_data.py`) — dead Mongo code
- `init.sql` comment claims Alembic manages schema (it doesn't)
- `users.py` unused `and_` import; trailing-slash conventions differ per router
- `reports.py` route declared `"/"` (307 for body-carrying POSTs)
- Admin `pages` computation `if total > 0 else 1` vs 0 elsewhere
- `library.py` inline schemas belong in `app/schemas/library.py`

## Verified non-issues (do NOT "fix")

- `get_current_user` returns None for invalid tokens (optional-auth semantics); required auth paths use `get_current_active_user` → 401/403 correctly.
- `ResourceResponse` is an explicit allowlist: no password_hash/telegram/file_hash leakage on detail/list/upload endpoints. The leak class is limited to endpoints returning raw ORM rows (C1).
- Password-protected resources: metadata is public **by design** (frontend fetches metadata to render the prompt); content gates (download/preview/preview-text) DO verify the password. Tests encode this.
- Access tokens survive password change until 15-min expiry (stateless JWT); refresh sessions are revoked server-side. By design; documented.
- `search.py` `q` LIKE is admin-surface-free (public), parameterized; wildcard escaping is a correctness nicety (M1), not injection.

## Schema drift (init.sql vs alembic vs models)

Runtime truth = `Base.metadata.create_all` from `app/models`. `init.sql` is a 6-line stub. Alembic 001 describes a **different, Postgres-shaped database that matches neither** (UUID PKs vs String PKs, `tags` ARRAY vs `tags_str` Text, `search_vector` tsvector vs none, audit_logs column-for-column different, departments/courses/collections absent). Decision: regenerate migration 001 from current metadata with SQLite dialect + `render_as_batch`, fix env.py, add alembic to requirements (Task 4.x).

## Test suite status

- Created in Phase 0: `backend/tests/` — conftest (isolated temp SQLite, StaticPool, patched before app import, telegram faked) + health/auth/resources/search/ratings/library/users/admin suites.
- Baseline: **76 passed, 2 xfailed (strict)** at commit time. xfail guards = C1; strict=True forces removal once fixed.

## Dependencies (grep-verified)

- Used: fastapi, sqlalchemy, aiosqlite, pyrofork, tgcrypto, python-jose, passlib, bcrypt, pyotp, qrcode, pydantic, pydantic-settings, email-validator, prometheus-client, python-dotenv, httpx (tests), aiofiles, python-multipart, uvicorn
- Unused: **redis[hiredis]**, **python-magic** (also needs libmagic absent from Dockerfile), **sentry-sdk** (settings exist but never read)
- Missing: **alembic** (declared nowhere, not installed)
