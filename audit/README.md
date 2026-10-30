# 20-Workstream Security & Bug Audit

> **Status: campaign complete (2026-10-28).** These reports are historical
> records — current project state lives in `docs/STATUS.md`; durable decisions
> in `docs/DECISIONS.md`. Do not edit these files to "update" them; append
> corrections to `docs/DECISIONS.md` instead.

Phase 1 is read-only. Each workstream writes one report to `audit/NN-*.md` with verified findings, severity, file:line, reproduction, impact, and a minimal proposed patch. No application code, database, or external service may be modified in Phase 1.

Phase 2 applies the consolidated fixes in controlled batches, with tests and a frontend typecheck/build.

| # | Workstream | Primary scope |
|---|---|---|
| 01 | Auth, MFA, sessions | `backend/app/api/v1/auth.py`, `password_reset.py`, `core/security.py`, user/session models; frontend auth context and auth pages |
| 02 | Authorization & IDOR | `deps.py`, ownership checks, `library.py`, `users.py`, `reports.py`, banned-user paths |
| 03 | Upload pipeline | `resources.py` upload, upload page, quota/duplicate/moderation/storage ordering |
| 04 | Download & preview | `resources.py` preview/download/preview-text, detail-page preview/download, MIME/XSS/cache |
| 05 | Resource CRUD/list | `resources.py` list/get/update/delete/my, `schemas/resource.py`, visibility/moderation/serialization |
| 06 | Ratings & reports | `ratings.py`, `reports.py`, rating/report models and schemas, aggregates/races |
| 07 | Admin backend | `api/v1/admin/**`, legacy `admin.py`, role gates, destructive operations, audit |
| 08 | Database & backup | `core/database.py`, `tasks/scheduled_backup.py`, `alembic/`, WAL/FK/transactions/migrations |
| 09 | Telegram & cache | `services/telegram.py`, `download_manager.py`, `cache.py`, bot commands, file cache |
| 10 | Search & filters | `search.py`, public departments/courses, stats/cache, query performance/leakage |
| 11 | Models & schemas | `models/**`, `schemas/**`, constraints, relationships, validation, type mismatches |
| 12 | Middleware & deploy | `main.py`, `middleware.py`, `config.py`, `Dockerfile`, `nginx.conf`, CI, dependencies |
| 13 | Users & profile | `users.py`, user schema, storage recalculation, password change, profile updates |
| 14 | Collections/library | `library.py`, collection models/schemas, ownership, duplicates, access control |
| 15 | Frontend shared | `lib/api.ts`, `auth-context.tsx`, hooks, token refresh, state machine, error handling |
| 16 | Frontend browse | `app/page.tsx`, `app/browse`, search components, cards, header search |
| 17 | Frontend detail/edit | `app/resources/[slug]/**`, preview/download/password/rating UX, stale refetch |
| 18 | Frontend admin | `app/admin/**`, role gates, endpoint mismatches, audit/clear-all, bulk actions |
| 19 | Frontend forms/UI | upload/auth/settings pages, `components/ui/**`, validation, a11y, multi-file, progress |
| 20 | Testing & CI | Test coverage, test plan, CI workflow, Dockerfiles, compose, build/typecheck/lint |

## Rules

- Verify every claim against source; no speculation without a file:line.
- Do not print secret values; cite locations only.
- Do not start the app, call Telegram, or mutate the SQLite database.
- Do not edit files outside your assigned report path.
- Return a short summary (counts + top 3 findings) to the parent agent.
