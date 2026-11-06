# Architecture Map

> What exists, where it lives, and where to look next. Backend deep-dive:
> `docs/backend.md`. Storage internals: `TELEGRAM_AND_DATABASE_GUIDE.md`.
> Rules: `AGENTS.md`. Current health: `docs/STATUS.md`.

## Repository layout

```
Students-main/
├── backend/                    # FastAPI + SQLAlchemy 2 (async) + aiosqlite
│   ├── app/
│   │   ├── main.py             # app factory, lifespan, /health, /metrics
│   │   ├── core/               # config, database, security (JWT/MFA), middleware
│   │   ├── models/             # SQLAlchemy models — the schema source of truth
│   │   ├── schemas/            # Pydantic request/response contracts
│   │   ├── api/v1/             # routers: resources, search, auth, users, ratings,
│   │   │   │                   #   library, password_reset, reports, stats + admin/*
│   │   │   └── admin/          # moderation, resources, courses, departments,
│   │   │                       #   users, reports, dashboard, seed
│   │   ├── services/           # telegram (blob storage), download_manager (disk
│   │   │                       #   LRU cache), cache (single-flight), stats, email, upload
│   │   └── tasks/              # scheduled_backup (midnight), cleanup (daily)
│   ├── alembic/                # migrations (SQLite-compatible)
│   ├── tests/                  # pytest suite (temp SQLite, Telegram faked)
│   └── student_library.db      # LIVE database — never seed or wipe (AGENTS.md #4)
├── frontend/                   # Next.js 14 App Router + TypeScript + Tailwind
│   ├── app/                    # routes (see jump table below)
│   ├── components/             # UI components; preview/ = client-side renderers
│   │   └── preview/FilePreview.tsx   # all inline renderers (9 formats)
│   ├── lib/api.ts              # API CONTRACT — additive changes only (AGENTS.md #1)
│   ├── lib/auth-context.tsx    # auth state, token refresh
│   └── public/                 # static assets
├── docs/                       # governed documentation (index below)
├── audit/                      # completed audit campaign reports (historical)
├── tasks/                      # completed upgrade campaign ledgers (historical)
├── Dockerfile + nginx.conf     # single-container deployment
└── .github/workflows/ci.yml    # CI (backend pytest + frontend job + image build)
```

## Frontend routes (`frontend/app/`)

| Route | Purpose |
|---|---|
| `page.tsx` (root route) | Homepage |
| `/browse` | Browse & search resources |
| /resources/[slug] | Resource detail: preview modal (fullscreen study mode), download, rating, edit |
| `/upload` | Upload form (drag & drop, multi-file, progress) |
| `/library` | User collections |
| `/dashboard` | User dashboard |
| `/profile`, `/settings` | Profile & account settings |
| `/auth/*` | Login / register / MFA setup |
| `/admin/*` | Admin panel (shared layout nav: dashboard, moderation, resources, users, departments, courses, reports, audit) |
| `/about`, `/report` | Info pages |
| `/dmca`, `/privacy`, `/terms` | Legal pages (compliance posture is binding — `PRODUCT.md`) |
| `/403` | Forbidden page |

## Where is X? (jump table)

| Need | Go to | Verify with |
|---|---|---|
| Add/change an API endpoint | `backend/app/api/v1/**` + mirror in `frontend/lib/api.ts` | `pytest tests/` + curl against :8000; contract stays additive |
| Change the data model | `backend/app/models/**` (+ Alembic migration if for existing DBs) | full pytest suite; `alembic upgrade head` on a DB copy |
| Auth, sessions, MFA, reset | `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/password_reset.py` | `test_security_hardening.py` + manual login/MFA flow |
| Upload / download / preview pipeline | `backend/app/api/v1/resources.py`, `backend/app/services/telegram.py`, `backend/app/services/download_manager.py`; frontend `frontend/app/resources/[slug]/page.tsx` + `frontend/components/preview/FilePreview.tsx` | real-browser test at 1440/768/375 + curl MIME/disposition checks |
| Admin surface | `backend/app/api/v1/admin/**`, `frontend/app/admin/**` | browser (admin login) + API matrix; envelope = `{results,total,page,page_size,pages}` |
| Search, filters, departments | `backend/app/api/v1/search.py`, `backend/app/api/v1/courses.py`, `backend/app/api/v1/departments.py`; `frontend/app/browse` | pytest + browser filter pass |
| Ratings / reports | `backend/app/api/v1/ratings.py`, `backend/app/api/v1/reports.py` | pytest (unique-rating race, report state machine) |
| Design system & theming | `DESIGN.md` (tokens, rationale); Tailwind classes | axe-core / Lighthouse + keyboard pass (WCAG 2.1 AA target) |
| Telegram storage & disk cache | `backend/app/services/telegram.py`, `download_manager.py`; full guide: `TELEGRAM_AND_DATABASE_GUIDE.md` | backend.md "Core invariants" + tests faking Telegram |
| Scheduled jobs | `backend/app/tasks/**` (wired in `main.py` lifespan) | test suite + logs (single process only!) |
| Deployment / Docker / nginx | `Dockerfile`, `nginx.conf`, `docs/DEPLOYMENT.md` | image build validation job in CI |
| Environment variables | `docs/OWNER_GUIDE.md` (owns the env reference) | — |
| CI | `.github/workflows/ci.yml` | workflow run |

## Documentation index (by role)

| Role | File | Owns |
|---|---|---|
| **Constitution** | `AGENTS.md` | Rules agents/contributors must obey; reading sequence |
| **Map** (this file) | `docs/ARCHITECTURE.md` | Structure, ownership, navigation |
| **Status** | `docs/STATUS.md` | Current health, open owner actions, delete-zone |
| **History** | `docs/DECISIONS.md` | Durable decisions, removals, incidents (append-only) |
| History (archive) | `audit/security-report.md`, `audit/quality-pass.md`, `tasks/findings.md`, `tasks/plan.md`, `tasks/ecc-loop.md` | Completed campaign records |
| Reference | `docs/backend.md` | Backend architecture + ops runbook (owns backend invariants) |
| Reference | `docs/API.md` | Endpoint reference (routes in code are authoritative) |
| Reference | `TELEGRAM_AND_DATABASE_GUIDE.md` | Storage/database internals |
| Reference | `docs/USER_GUIDE.md`, `docs/OWNER_GUIDE.md`, `docs/DEPLOYMENT.md` | End-user, admin, and deployment guides |
| Reference | `PRODUCT.md`, `DESIGN.md` | Product intent; design system |
| Rules | `CONTRIBUTING.md` | Contribution workflow |

**Discipline:** one canonical owner per fact — link, don't copy. When changing
structure → update this map in the same change; status changes → `STATUS.md`;
decisions/removals → `DECISIONS.md`.
