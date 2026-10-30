# Deployment Guide

> The project deploys as **one container**: Nginx (port 80) serves the built
> Next.js frontend and proxies `/api`, `/docs`, `/openapi.json` to the FastAPI
> backend (port 8000). Data model: SQLite on disk + files stored in Telegram
> channels. Backend internals: `docs/backend.md`. Storage internals:
> `TELEGRAM_AND_DATABASE_GUIDE.md`.

Two supported paths:

| Path | Use when |
|---|---|
| **Koyeb (recommended)** — below | Simplest PaaS deploy: push-to-deploy, free TLS subdomain, no server to manage |
| **Any host with Docker** — bottom section | VPS / other PaaS; runs the same image with `docker run` |

## Required environment variables

All values come from `backend/app/core/config.py` (field names uppercased).

**Security (always set in production — the app refuses to boot a production
deployment with an empty JWT secret):**

```env
SECRET_KEY=<openssl rand -hex 32>
JWT_SECRET_KEY=<openssl rand -hex 32>
HMAC_SECRET_KEY=<openssl rand -hex 32>
ENVIRONMENT=production
```

**Telegram storage (uploads are dead without these; the app boots without
them but file operations fail):**

```env
TELEGRAM_API_ID=<my.telegram.org api id>
TELEGRAM_API_HASH=<my.telegram.org api hash>
TELEGRAM_BOT_TOKEN=<BotFather token>
TELEGRAM_PRIMARY_CHANNEL=<primary channel id>
TELEGRAM_BACKUP_CHANNEL=<backup channel id>
TELEGRAM_OWNER_ID=<your telegram user id — bot commands are owner-only>
```

The bot must be an **admin** of both channels. Backups land daily in the
backup channel (`tasks/scheduled_backup.py`).

**First-boot admin (one-time):** setting these creates an admin account
automatically on a fresh database:

```env
INITIAL_ADMIN_EMAIL=<email>
INITIAL_ADMIN_PASSWORD=<strong-password>
```

**Public URL** (used in emails/links): `APP_URL=https://<your-domain>`

**Optional:** `SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD/EMAILS_FROM_EMAIL`
(password-reset emails), `MAX_FILE_SIZE_MB` (50), `RATE_LIMIT_PER_MINUTE`
(60), `ENABLE_RATE_LIMITING` (true).

> **Behind a shared edge proxy (Koyeb, Fly, etc.):** `X-Forwarded-For` is only
> trusted from `TRUSTED_PROXIES` IPs (default: loopback only) — deliberate
> hardening. Behind PaaS edges all visitors share one proxy IP, so per-IP
> rate limits would lump everyone into a single bucket. Raise
> `RATE_LIMIT_PER_MINUTE` (e.g. 600) or leave `ENABLE_RATE_LIMITING=false`
> until you can pin trusted proxy IPs.

---

## Deploy to Koyeb

The root `Dockerfile` is Koyeb-ready: it builds the frontend with
`NEXT_PUBLIC_API_URL=""` (the frontend then calls same-origin paths through
Nginx — no CORS configuration needed) and exposes **only port 80**.

### 1. Create the service

1. Sign up at [app.koyeb.com](https://app.koyeb.com). A card is pre-authorized
   (Pro hold) — [downgrade to Starter afterwards](https://www.koyeb.com/pricing);
   the Free web service instance is billed $0.
2. **Create Service → GitHub**, connect the `timstan627/Library` repo, branch
   `main`.
3. Builder: **Dockerfile** (auto-detected at the repo root — no buildpack).

### 2. Networking

- **Exposed port**: replace the default with `80:http`
  (the image serves Nginx on 80; nothing listens on 8000 externally).
- **Route**: `/:80` (default).
- **Health check**: protocol **HTTP**, port `80`, path `/openapi.json`
  (Nginx proxies it to FastAPI — `/health` itself is not proxied). Set a
  **grace period of ~30s** so the build's first boot isn't flapped.

### 3. Instance & scaling

| | Free instance | Production |
|---|---|---|
| RAM / vCPU | 512 MB / 0.1 shared (always $0) | e.g. `small` (paid, per-second billing) |
| Region | Frankfurt or Washington DC only | your choice |
| Scaling | fixed at 1 — **must stay 1** | set **min = max = 1** |
| Volumes | ❌ not supported | ✅ attach one (see persistence) |
| Idle behavior | **scales to zero after 1h idle** | always on |

**Why 1 instance everywhere:** rate limiting, auth lockout, password-reset
tokens, view tracking, and stats are **in-process memory**
(`docs/backend.md` "Core invariants"). Two instances = two inconsistent
brains. Never enable autoscaling for this service.

**Why not the free instance with real data:** its disk is ephemeral **and it
sleeps after 1 idle hour** — on every wake-up the database is empty again.
Free = demos/previews only. On 512 MB, ~50 MB uploads (buffered in RAM) can
also OOM — production wants the paid instance size up.

### 4. Environment variables

Add these in **Services → your service → Settings → Environment variables**:

- All **Security** and **Telegram** variables from the table above.
- `APP_URL=https://<app-name>.koyeb.app` (fill in after the first deploy —
  the subdomain is shown once the service is healthy).
- For a fresh production DB: `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`.

### 5. Deploy & verify

Click **Deploy**. The first build compiles Next.js + installs Python deps
(~5–10 min); later builds reuse cache and only redeploy on push to `main`
(push-to-deploy is automatic with GitHub services).

When the service turns **Healthy**:

```bash
# API docs served through the Koyeb domain proves the whole chain works
curl -s https://<app-name>.koyeb.app/openapi.json | head -c 200
# Register a user / log in, then upload a small file
```

### 6. Persistence (this is the one real decision)

Files live in Telegram channels — they survive anything. What is at risk is
the **SQLite metadata DB** on the instance disk:

| Setup | DB fate |
|---|---|
| Free instance, no volume | **Wiped on every restart, redeploy, and idle wake-up.** Preview only. |
| Paid instance + Volume | Persistent. Recommended. |

Paid-volume setup:

1. Region: instance must run in `was` (Washington DC) or `fra` (Frankfurt) —
   volumes are region-bound, same as the instance.
2. Create a Volume (a few GB is ample for metadata) and mount it at **`/data`**
   (Service → Settings → Volumes).
3. Point the DB at it:

   ```env
   DATABASE_URL=sqlite+aiosqlite:////data/student_library.db
   ```

   The backup copy (`student_library_backup.db`) and corrupt-DB quarantine are
   created **next to the DB file** — mounting `/data` gives you automatic
   local backup + auto-restore-on-corruption, plus the daily Telegram backup.
4. Redeploys, restarts, and domain changes now keep all users/resources/ratings.

Migrations: **none to run by hand.** Startup runs `Base.metadata.create_all`
for fresh DBs plus idempotent `_ensure_schema_upgrades()` patches on existing
ones; the Alembic head produces an identical schema.

### 7. Custom domain (optional)

Service → Domains → add your domain, then CNAME / ALIAS your DNS record to
the target Koyeb shows. TLS is automatic. Update `APP_URL` afterwards.

### Koyeb troubleshooting

| Symptom | Cause / fix |
|---|---|
| Service never healthy | Check **Deployment logs**; most common: port not exposed as `80:http`, or missing `JWT_SECRET_KEY` with `ENVIRONMENT=production` (startup refuses). |
| Build fails on frontend | Ensure the GitHub app has access to the repo; the repo root `Dockerfile` builds `frontend/` then `backend/` — check the build log stage. |
| Everyone gets 429s | Shared edge proxy IP — see the note about `RATE_LIMIT_PER_MINUTE` / `ENABLE_RATE_LIMITING`. |
| 502 on API but frontend fine | uvicorn crashed (Telegram `client.start()` with bad bot token retries/log — check logs); the Docker healthcheck covers backend liveness. |
| Uploads OOM / killed | 512 MB is too little for 50 MB RAM-buffered uploads — move to a bigger instance, or lower `MAX_FILE_SIZE_MB`. |
| Data vanished after idle | Free-instance sleep wiped the ephemeral disk — attach a paid Volume and set `DATABASE_URL` (section 6). |

---

## Deploy anywhere with Docker (VPS / other PaaS)

The same image runs on any Docker host:

```bash
git clone <repository-url> student-library && cd student-library

docker build -t student-library .

docker run -d --name student-library -p 80:80 \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32) \
  -e HMAC_SECRET_KEY=$(openssl rand -hex 32) \
  -e ENVIRONMENT=production \
  -e APP_URL=https://yourdomain.com \
  -e TELEGRAM_API_ID=<id> \
  -e TELEGRAM_API_HASH=<hash> \
  -e TELEGRAM_BOT_TOKEN=<token> \
  -e TELEGRAM_PRIMARY_CHANNEL=<channel> \
  -e TELEGRAM_BACKUP_CHANNEL=<backup-channel> \
  -e TELEGRAM_OWNER_ID=<owner> \
  -v student-library-data:/data \
  -e DATABASE_URL=sqlite+aiosqlite:////data/student_library.db \
  student-library

# TLS: terminate SSL in your existing edge (Caddy/Nginx/LB) and forward to :80,
# or run Certbot in front — the container speaks plain HTTP on port 80.
```

Put a persistent volume on `/data` for real data (same reasons as Koyeb).
Behind your own Nginx on the host, also set
`TRUSTED_PROXIES=<edge-ip>` so real client IPs are honored.

Health/metrics: container HEALTHCHECK probes `http://127.0.0.1:8000/health`;
Prometheus metrics are at `/metrics` internally; public chain check is
`/openapi.json`.
