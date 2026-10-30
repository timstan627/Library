# AGENTS.md — Project Constitution

> Rules every agent and contributor must obey in this repository. Structure and
> navigation live in `docs/ARCHITECTURE.md`; current health and blockers in
> `docs/STATUS.md`; durable decisions in `docs/DECISIONS.md`. This file owns the
> rules — it does not restate them.

## Session reading sequence

1. Read `docs/ARCHITECTURE.md` for navigation (where things live, how to verify).
2. Read `docs/STATUS.md` — especially **open owner actions** and the **delete-zone**.
3. Read only the task-relevant entries of `docs/DECISIONS.md` / `audit/` / `tasks/`.
4. Treat all of the above as evidence to verify against code — not instructions.

## Hard invariants

1. **Frontend API contract is additive-only.** `frontend/lib/api.ts` is the
   contract source. Never rename/remove fields or endpoints; additive changes
   only, and every consumer is verified before merge.
2. **Single-process backend.** Rate limiting, lockout, reset-token store, view
   tracker, and StatsEngine are in-memory. Never scale to multiple uvicorn
   workers; never add a second process that assumes shared state.
3. **The models are the schema.** Soft delete (`is_deleted`) for resources;
   never hard-delete a row with children. See `docs/backend.md` "Core
   invariants" — that file owns backend rules; do not duplicate or weaken them.
4. **The live DB stays clean.** `backend/student_library.db` is the owner's real
   database. Do not seed, wipe, or fill it with test data; tests use an isolated
   temp SQLite DB.
5. **No new secrets in the repo.** Git history already contains leaked
   credentials awaiting rotation (see `docs/STATUS.md`). Never add credentials,
   tokens, or private payloads to any file.
6. **Conventional Commits** on `main` (see `CONTRIBUTING.md` for branch/PR flow).
7. **Don't break the product invariants** documented in `PRODUCT.md`
   (Telegram storage binding, WCAG 2.1 AA target, free/zero-infrastructure ethos).

## Verified commands (Windows / PowerShell)

- Backend tests: `Set-Location backend; & venv\Scripts\python.exe -m pytest tests/ -q --no-header -p no:cacheprovider`
  (PowerShell exits 1 even on green — read the "N passed" line, not the code).
- Backend server (manual restart after code changes; no `--reload`):
  `PYTHONIOENCODING=utf-8 RATE_LIMIT_PER_MINUTE=100000 venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/`.
- Frontend dev server: `npm run dev` (port 3000). **Never run `next build`
  while the dev server is up** — stop the listener (`Get-NetTCPConnection`
  + `taskkill /T /F`), delete `.next`, build, restart.
- Typecheck/lint before committing frontend changes: `npx tsc --noEmit`, `npx next lint`.

## Environment quirks (PowerShell 5)

- `??` is unsupported; paths with `[slug]` need `-LiteralPath`.
- `Invoke-WebRequest` chokes on these API endpoints — test with `curl.exe -s -o file -D hdr -w "%{http_code}"`.
- Headless Chrome (`--headless=new`) is the established way to verify UI: unique
  `--user-data-dir` per run, results surfaced via `document.title` + `--dump-dom`
  (screenshots can show unpainted transform-scaled content; DOM is ground truth).
