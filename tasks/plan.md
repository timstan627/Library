# Implementation Plan: Backend Production-Grade Upgrade

## Overview

Full audit + upgrade of the FastAPI backend (SQLite/SQLAlchemy, Telegram blob storage, ~7.2k lines / 56 files) to production grade: correctness, security, data integrity, API contract consistency, modularity, performance, observability, tests, and CI. Every endpoint and service file is read line-by-line; findings are verified against source before fixing. Frontend contract (cataloged from `frontend/lib/api.ts` + page usage) must not break.

## Architecture Decisions

- **Keep SQLite + aiosqlite** (design uses single-file DB + Telegram storage). Production-grade = correct pragmas per connection, safe backups, WAL, busy_timeout — not a Postgres migration.
- **Keep in-memory rate limiting/cache** (single-process design). Document the multi-worker limitation instead of adding Redis (already an unused dep — remove it).
- **Schema changes** ship as an Alembic migration (dedupe + unique index + performance indexes) plus idempotent startup ensures; `create_all` stays for fresh DBs only.
- **No breaking API contract changes.** All response shapes keep `results/total/page/pages/...`; changes are additive (new fields, safer serialization).
- Tests via **pytest + pytest-asyncio + httpx ASGI transport** against a temp SQLite DB — no external services.

## Verified Findings (my audit)

### Critical
1. `/search/popular` + `/search/recent` return raw ORM objects — leaks `uploader.password_hash`, `email`, `mfa_secret`, `telegram_file_id/channel_id`, `file_hash` (verified live). → response_model with safe summary schema.
2. `dbinit_handler` telegram.py:378 uses `Path` — never imported → NameError; `/dbinit` broken.
3. SQLite `PRAGMA foreign_keys=ON` set once on one pooled connection — FK enforcement effectively off everywhere else; no `busy_timeout` → "database is locked" under concurrency.

### High
4. `backup`/`create_backup`/`dbsend` copy the live WAL DB file with `shutil.copy2` — torn/inconsistent backup risk → use SQLite backup API.
5. Ratings: no unique (user_id, resource_id) — race double-insert double-counts aggregates; `rating_sum +=` non-atomic lost updates.
6. Views/downloads `+= 1` read-modify-write — lost updates under concurrency → atomic `UPDATE ... SET x = x + 1`.
7. Register: check-then-insert email race → 500 on duplicate; catch IntegrityError → 409.
8. CI (`.github/workflows/ci.yml`) is fictional: Postgres+Redis services (unused), `Dockerfile.prod`/`docker-compose.prod.yml` missing, runs nonexistent pytest suite.
9. `User.resources` + `User.sessions` relationships `lazy="selectin"` — every authenticated request eagerly loads the user's ENTIRE resource list + sessions.
10. Department filter broken end-to-end: browse sends `department` → `/search` and `/resources` accept + drop it; `/search/filters` returns hardcoded `departments=[]`; upload accepts `department` and never stores `department_id`.

### Medium
11. `search_resources` swallows all exceptions → 200 with empty results on DB failure (masks outages).
12. Search `q` LIKE wildcards unescaped (`%`/`_` injection); `/filters` leaks pending-resource course codes (missing approved filter).
13. `library.remove_item` checks item existence before ownership → 404-vs-403 oracle; `add_items` N+1 per resource_id; negative `limit` unclamped (`/library/recent`).
14. `upload_resource` buffers whole file in RAM (OK at 50MB cap; document + stream-to-disk improvement).
15. Slug collision → 409 to user instead of retry with new suffix.
16. download_manager: blocking `shutil.copy2`/`stat`/`open` in async paths; temp-file leak if file > cache threshold; `_stream_from_disk` falsely "async".
17. Dead code: `telegram.download_file`, `telegram.stream_file`, `download_manager.stream_file/get_file_bytes`, whole 500MB in-memory `FileCache` (nothing calls them).
18. `cache.py` StatsEngine: declared `_lock` never used; thundering-herd duplicate fetch on concurrent miss.
19. `_backup_upload` fire-and-forget task not referenced → GC risk; backup message ids never stored in `backup_telegram_*` columns.
20. `ResourceResponse.department: Optional[str]` vs `Resource.department` relationship object — latent 500 once any resource gets a department_id; `ResourceUpdate` can't set password/visibility=password (contract gap vs upload).
21. Auth deps duplication (`get_admin_user` vs `require_admin`, two current-user variants); 404 for deleted-user-with-valid-token should be 401; logout revokes ALL sessions (document or scope); no per-email-only lockout (rotating IP brute force).
22. Stats query functions live in `main.py`; dashboard full/lite duplicate logic; `pending_reports` try/except-pass swallows errors.
23. In-memory rate limiter/AuthRateLimiter/view tracker keys never evicted globally → slow memory growth.
24. requirements.txt: `redis`, `python-magic` likely unused (verify by grep); no mypy/black config; no `.env.example`.
25. Collection.emoji corrupted default `"dY\"?"` in model.
26. Root dev scripts (`debug_db.py`, `fix_admin.py`, `inspect_*.py`) + `debug_db.py` — cleanup/relocate; ensure none hold credentials.
27. Health endpoint doesn't exercise DB; `/metrics` gated behind debug.

### Low / Nit
28. `TokenResponse.expires_in` default 900 vs config 3600 (unused default), `sort_by=rating` sorts by sum not average, `traceback.print_exc()` in upload error path, `asyncio.get_event_loop()` dead local, `semaphore._value` private access, models/audit.py 5-line re-export.

## Task List

### Phase 0 — Safety net (tests first)
- [x] Task 0.1: pytest scaffolding — `backend/tests/` with conftest (temp SQLite DB, ASGI client, user/admin fixtures, factories) + `pytest.ini`/pyproject config.
- [x] Task 0.2: Baseline smoke tests encoding current contracts: auth (register/login/refresh/logout/me/MFA), resources (list/my/detail/upload-mock/delete/update), search+filters, ratings CRUD, library collections CRUD, admin (moderation/courses/departments/users/reports/resources/dashboard), health. Upload tests mock `telegram_service`.
- [x] Checkpoint 0: suite green against current code; failures = pre-existing bugs (recorded in findings.md).

### Phase 1 — Critical security & correctness
- [x] Task 1.1: Safe serialization for `/search/popular|recent` (+ any other ORM-leaking endpoints found by auditors) via response schemas.
- [x] Task 1.2: DB engine: per-connection event listener (foreign_keys, busy_timeout, WAL), pool config; robust init_db.
- [x] Task 1.3: Backup integrity — sqlite3 backup API (async wrapper) for `create_backup`, scheduled backup, `dbsend`.
- [x] Task 1.4: Ratings integrity — unique index + startup dedupe + atomic aggregate updates, IntegrityError fallback, unique constraint in model.
- [x] Task 1.5: Atomic counters (views/downloads/storage) via UPDATE statements.
- [x] Task 1.6: Register IntegrityError → 400. (Slug retry: pre-existing slug already embeds a random suffix; 409 path kept as safety net.)
- [x] Task 1.7: `/dbinit` Path import fix + FloodWait retry cap; create_task reference retention.
- [x] Checkpoint 1: full suite green (78 passed); commit `1bd95ad`.

### Phase 2 — API contract & consistency
- [x] Task 2.1: Department feature completion — upload/update stores `department_id` (resolve by name/code, unknown → 400), `/search` + `/resources` apply `department` filter, `/search/filters` returns real active departments + approved-only options, `ResourceResponse` exposes `department_id`/`department_name`.
- [x] Task 2.2: Search fixes — no exception swallowing, escape LIKE, rating sort by average.
- [x] Task 2.3: Auth contract — typed RefreshRequest (422), deleted-user token → 401, per-email account-wide lockout, register IntegrityError → 400, admin deps unified as aliases.
- [x] Task 2.4: Library fixes — ownership oracle single-query, batch verify (IN), limit clamp + validation, inline schemas moved to `app/schemas/library.py`.
- [x] Task 2.5: `ResourceUpdate` parity (visibility=password + password set/remove semantics).
- [x] Task 2.6 (pulled in): password-reset hardening (M7) — shared complexity validator, one-token-per-account, atomic single-use pop, is_active re-check, per-email throttle, audit log.
- [x] Checkpoint 2: suite green (102 passed); commits for both halves of the phase.

### Phase 3 — Modularity & performance
- [x] Task 3.1: Stats queries extracted to `services/stats.py`; `admin_dashboard_full` cache key deleted (zero consumers, ~40k wasted queries/day); try/except-pass died with it; main.py slimmed to app wiring.
- [x] Task 3.2: Eager-loading fixed — `lazy="raise"` on all implicitly-unread relationships (User.sessions/resources/collections, Session.user, Resource.course/moderated_by/deleted_by, Rating.resource, Collection.user, CollectionItem.resource); selectin kept only where serialization properties / flush-time cascades need it.
- [x] Task 3.3: download_manager — FS work via to_thread, dead stream/bytes paths removed, `release()` contract for uncached temp downloads wired into preview/download (BackgroundTask) and preview-text (inline after read); download error detail no longer echoes str(e).
- [x] Task 3.4: Dead code removed — telegram.download_file/stream_file, download_manager stream paths, FileCache (500MB) + CacheService file API; StatsEngine per-key single-flight; telegram drops cache_service/os imports.
- [x] Task 3.5: Eviction hygiene — shared time-gated `sweep_windowed()` on AuthRateLimiter + RateLimitMiddleware + password-reset email throttle (newest-N caps); `_view_tracker` inline eviction verified adequate; Collection.emoji verified non-issue (UTF-8 artifact).
- [x] Checkpoint 3: 104 passed; live smoke green (/health + /api/v1/stats); commits `7ad88af` + Task 3.1.

### Phase 4 — Ops hardening
- [ ] Task 4.1: `/health` with DB check; structured logging fixes (no print_exc); request-id header.
- [ ] Task 4.2: `.env.example`; requirements prune (grep-verified); CI rewrite to match reality (SQLite tests, no fake services, correct Dockerfile refs, coverage gate).
- [ ] Task 4.3: Script cleanup (relocate/`seed_data.py` keep; delete debug one-offs); Dockerfile review per auditor report.
- [ ] Task 4.4: `docs/backend.md` (architecture, API conventions, ops runbook: backup/restore, rate limits, multi-worker caveat).
- [ ] Checkpoint 4: CI config validated locally (docker build if feasible), docs committed.

### Phase 5 — Final verification
- [ ] Full test suite + type check; live restart of backend; smoke all pages; security re-scan of changed endpoints; commits per phase (already batched along the way).

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests change behavior assumptions | Hidden regressions | Phase 0 tests encode current contract first; changes after are deliberate |
| Alembic migration on live dev DB | Data loss | Test migration on a DB copy first; keep backup; no destructive ops |
| Removing "dead" code breaks unseen caller | Runtime 500 | Grep-verified zero call sites + full suite + live smoke |
| Contract drift breaks frontend | UI breakage | Frontend API surface cataloged; additive-only changes; smoke after each phase |
| FloodWait/Telegram flakiness in tests | Flaky suite | Telegram service mocked in all tests |

## Open Questions
- (subagent audit findings pending — will merge into tasks before execution)
- Whether `redis`/`python-magic`/`sentry-sdk` removal is desired (I'll remove only if grep proves unused and note it).
