# Backend Architecture & Ops Runbook

Stack: **FastAPI + SQLAlchemy 2 (async) + aiosqlite/SQLite + Telegram channels as blob storage.**
Runtime target: a **single uvicorn process**. Anything below is written for that reality.

```
backend/
├── app/
│   ├── main.py          # app factory, lifespan (startup/shutdown), /health
│   ├── core/            # config (Settings), database (engine/health/backup), security (JWT/hash/MFA), middleware
│   ├── models/          # SQLAlchemy models — the source of truth for the schema
│   ├── schemas/         # Pydantic request/response contracts (app/schemas/library.py, user.py, ...)
│   ├── api/v1/          # routers: resources, search, auth, users, ratings, library, password_reset,
│   │                    #   admin/{moderation,resources,courses,departments,users,reports,dashboard,seed}
│   ├── services/        # telegram (channel storage), download_manager (disk LRU cache),
│   │                    #   cache (StatsEngine single-flight), stats (dashboard queries), email, upload
│   └── tasks/           # background schedulers: scheduled_backup (midnight), cleanup (daily)
├── alembic/             # migrations (SQLite-compatible; see "Migrations")
├── tests/               # pytest suite (isolated temp SQLite, Telegram faked)
├── requirements.txt     # runtime deps only
└── requirements-dev.txt # pytest/black/isort/mypy/httpx
```

## Core invariants (do not break these casually)

1. **Single process.** Rate limiting (`RateLimitMiddleware`), auth lockout
   (`AuthRateLimiter`), the password-reset token store, the view tracker, and
   StatsEngine are all **in-memory**. Running >1 worker forks this state per
   worker: limits become per-worker and background schedulers run N times.
   Scale up by scaling the whole single process (or move state to Redis first).
2. **The models are the schema.** `init_db()` runs `Base.metadata.create_all`
   for fresh databases plus idempotent `_ensure_schema_upgrades()` patches
   (dedupe + `CREATE UNIQUE INDEX IF NOT EXISTS`) for pre-existing ones. The
   Alembic 001 migration is derived from the same metadata, so both paths
   produce identical schemas.
3. **Soft delete.** Resources carry `is_deleted`/`deleted_at`; rows are purged
   only by the daily cleanup task (child rows first). Never hard-delete a
   resource row that still has ratings/downloads children.
4. **Uncounted-by-default reads.** Most relationships are `lazy="raise"` —
   touching them without an explicit `selectinload` fails loudly instead of
   silently eager-loading object graphs per request. The few `selectin`
   relationships that remain (e.g. `Resource.uploader/department`,
   `Collection.items`) are needed by serialization properties or flush-time
   cascades — see the comments on each relationship.
5. **Atomic counters.** View/download/storage counters are updated with
   `UPDATE ... SET x = x + 1` statements, never read-modify-write on ORM
   instances (concurrent requests would lose increments). Likewise never mix
   `db.execute(update(...))` with `instance.attr += 1` in one request — the
   RETURNING sync double-counts; use `db.refresh(...)` after the UPDATE.

## Request flow (download path)

```
GET /resources/{id}/download
  ├─ visibility/moderation gate (_ensure_viewable) + password check
  ├─ download_manager.get_file(message_id, channel_id)
  │    ├─ disk LRU cache HIT → return cached path
  │    └─ MISS → Telegram download to temp file
  │         ├─ fits cache (≤25% of cache max) → copied into cache, temp deleted
  │         └─ too big → temp path returned as "unmanaged"
  ├─ download logged + downloads counter incremented atomically
  └─ FileResponse(..., background=BackgroundTask(download_manager.release, path))
       → release() deletes the path ONLY if it was an unmanaged temp file,
         and only AFTER the response finished streaming
```

Endpoints returning files **must** attach the release background task; the
text-preview endpoint releases inline right after reading (content is in
memory, nothing streams from the path anymore). Skipping this leaks temp files
in the system temp dir.

## Caching & stats

- **StatsEngine** (`app/services/cache.py`): registered stat keys
  (`public_stats` 60s, `admin_dashboard_lite` 30s, `moderation_stats` 30s) with
  a 15s background refresh loop and **per-key single-flight** — concurrent
  misses await one shared fetch instead of stampeding the DB. Mutation hooks
  (`invalidate_on_upload/moderation/delete/user_change`) mark entries stale;
  stale data is served on refresh failure.
- Stat queries live in `app/services/stats.py` (not main.py). Response shapes
  are API contract — the admin dashboard and home page read them verbatim.
- The Telegram **file** cache is the disk LRU in `download_manager` (1 GB
  default). There is deliberately **no** in-memory file cache.

## Security model

- JWT access (60 min) + refresh (30 days, rotated on use, stored hashed in the
  `sessions` table). Logout revokes **all** sessions of the user (documented
  product decision).
- Login lockout is two-window: per `(ip, email)` (5 fails / 15 min) **and**
  account-wide per email (3× budget) — rotating-IP brute force trips the
  second window. Successful login clears both.
- Password reset: in-memory store of **SHA-256 digests only**, one live token
  per account (new request voids the old link), atomic single-use `pop()`,
  `is_active` re-checked on confirm, 3 requests/hour per email, successful
  resets audited. A rejected weak password does NOT burn the link (422 happens
  in body validation before the handler).
- Rate limiting is trusted-proxy aware: `X-Forwarded-For` is honored only when
  the direct peer is in `TRUSTED_PROXIES` (default `127.0.0.1,::1`). In tests,
  httpx presents `127.0.0.1` so XFF works without monkeypatching.
- Global sweepers bound every in-memory dict (`sweep_windowed()`): expired
  buckets dropped, newest-N caps (50k auth / 100k rate-limit / 10k reset)
  prevent memory growth under scanner traffic.
- Never put `str(e)` of internal exceptions into client-visible `detail` —
  log it, return a generic message.

## Telegram storage

- Files are documents in a primary channel; a backup channel receives the
  nightly DB snapshot (created via the SQLite backup API — consistent copy,
  never the live file) and FloodWait retries are capped.
- The Pyrogram session and channel IDs come from env (`TELEGRAM_*`, see
  `backend/.env.example`). Loss of the session file = re-login required.
- Backup message IDs are not yet persisted (finding M12 residual) — the
  backup channel is scanned by timestamp caption convention.

## Migrations (Alembic)

- `alembic/env.py` imports `Base` from `app.core.database` and all models via
  `import app.models`; URL = the app's own `DB_URL`; `render_as_batch=True`
  (required for any SQLite ALTER).
- 001 creates the full schema from `Base.metadata` (create-all semantics,
  idempotent per table).
- **Adopting Alembic on an existing database** (one that was bootstrapped by
  `init_db`): run `alembic stamp head` once, then use `upgrade head` from then
  on. Never `upgrade` a stamp-only DB — 001 would be a no-op anyway, but the
  stamp makes intent explicit.
- New migrations: `alembic revision --autogenerate -m "..."`, review the
  output (SQLite batch ops), keep them idempotent where possible.

## Health & observability

- `GET /health` exercises the DB via `check_db_health()`; 503 when
  degraded/critical. Issue details go to server logs only (public body stays
  minimal — file sizes/user counts must not leak).
- `X-Request-ID` on every response: echoed when the client sends a safe id
  (1–64 of `[0-9a-zA-Z_.-]`), else generated (`uuid4().hex`). Included in the
  global 500 log line and error body for support correlation.
- `/metrics` (Prometheus) is mounted only when `DEBUG=true`.

## Tests

- `pytest tests/` from `backend/` (deps: `requirements-dev.txt`).
- The suite runs against an **isolated temp SQLite** (StaticPool, patched
  before app import); the live DB is never touched. Telegram is faked;
  `fake_download_file` in conftest patches `download_manager` with a
  `get_file` + `release` stub.
- Limiter/reset state is cleared between tests by conftest.
- Known PowerShell quirk on Windows: the run may print stray
  `ValueError: I/O operation on closed file` lines and exit code 1 even when
  green — read the `N passed` line.

## Ops quick reference

| Task | How |
|------|-----|
| First boot | `uvicorn app.main:app` — init_db creates schema, seeds admin from `INITIAL_ADMIN_EMAIL/PASSWORD` |
| Nightly backup | automatic (midnight IST scheduler) → Telegram backup channel |
| Manual DB backup | POST `/api/v1/admin/dbsend` (admin) |
| Restore | stop app; replace `student_library.db` with a restored snapshot (auto-recovery also quarantines corrupt files and restores the local backup copy) |
| Adopt migrations on existing DB | `alembic stamp head` once |
| New migration | `alembic revision --autogenerate -m "..."` → review → `alembic upgrade head` |
| Prod image | `docker build backend/` (non-root, HEALTHCHECK, runtime deps only) |
| Env vars | see `backend/.env.example` |

## Known residual gaps (tracked in tasks/findings.md)

- Admin course/department delete cascades hard-delete resource rows (H2) —
  Telegram files orphaned; needs a soft-delete + file-cleanup design.
- Backup message ids not persisted (M12 residual).
- `semaphore._value` private access in download stats (cosmetic).
- Upload buffers the whole file in RAM (acceptable at the 50 MB cap; stream
  to disk is the eventual fix).
- The leaked MongoDB Atlas credential must be rotated by the owner — deleting
  the scripts does not scrub git history.
