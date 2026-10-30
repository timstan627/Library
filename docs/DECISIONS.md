# Decision & History Log

> Durable governance decisions, intentional removals, replacements, and material
> incidents. **Append-only** — correct stale claims with a new dated entry; never
> silently rewrite. Routine commits and fixes live in Git; campaign detail lives
> in `audit/` and `tasks/`. Current state: `docs/STATUS.md`.

Format: `[YYYY-MM-DD] type | decision — rationale; evidence`.

---

- [2026-10] decision | **SQLite + aiosqlite retained** (no Postgres migration); production-grade achieved via per-connection pragmas, SQLite backup API, WAL, busy_timeout — rationale: single-file, zero-config DB is a product principle; evidence: `tasks/plan.md` Architecture Decisions, `tasks/findings.md` H6.
- [2026-10] decision | **In-memory rate limiting / lockout / caches retained; single-process backend** — rationale: student-operator simplicity; multi-worker forked state documented as a hard invariant instead; evidence: `docs/backend.md` "Core invariants".
- [2026-10] decision | **Telegram channels as blob storage is binding** (unlimited, free storage; zero external deps) — rationale: core product differentiator; evidence: `PRODUCT.md` Brand Commitments, `TELEGRAM_AND_DATABASE_GUIDE.md`.
- [2026-10] policy | **Frontend API contract (`frontend/lib/api.ts`) is additive-only** — rationale: parallel frontend/backend safety; evidence: `AGENTS.md`, `tasks/plan.md`.
- [2026-10] removal | **13 dead Mongo/Beanie root scripts deleted** (`scripts/*` + root) — contained live credentials; `clear_resources.py` could wipe a remote DB unconditionally; **credential rotation remains an owner action**; evidence: `tasks/findings.md` C4/H10, `docs/STATUS.md`.
- [2026-10] removal | **Unused dependencies removed** (redis, python-magic, sentry-sdk); dev tooling split into `requirements-dev.txt`; alembic added — rationale: lean prod image; evidence: `tasks/findings.md` M14.
- [2026-10] removal | **Fictional CI replaced** (Postgres/Redis services, missing prod-file refs, nonexistent suite) — reality-based: SQLite pytest, coverage artifact, frontend job, image-build validation; evidence: `tasks/findings.md` H9.
- [2026-10-27] incident-fix | **Full quality & bug-fix pass** — admin nav, moderation history, department toggle (POST→PATCH + CORS), a11y fixes; browser-verified; evidence: `audit/quality-pass.md`.
- [2026-10-28] incident-fix | **Security audit closed** — 22 confirmed findings fixed (most serious: unapproved-content read/serve + client-declared MIME → stored XSS), 2 backend dep CVEs fixed, runtime re-probed; evidence: `audit/security-report.md`.
- [2026-10-29] decision | **Admin safety model hardened** — cascade deletes now 409 when children exist (no hard DELETE of resources); bulk ops capped; atomic moderation state transitions; unified pagination envelope `{results,total,page,page_size,pages}` across admin endpoints; audit-log failure never gates a user action; evidence: `tasks/findings.md` H2/H5/M15/M5/M6, commits `cce7296`, `0027762`, `73d99d7`, `9410434`.
- [2026-10-30] decision | **Inline client-side previews for all 9 uploadable formats** (hybrid model: client-side JS now, LibreOffice server-side later if needed); ZIP renders a file listing — evidence: commit `542d7a7`.
- [2026-10-30] replacement | **PPTX renderer replaced with `@aiden0z/pptx-renderer` 1.4.0** (lazy-loaded chunk; windowed slide mounting; IntersectionObserver scrollContainer) — evidence: commit `dcce22f`; old renderer in delete-zone (`docs/STATUS.md`).
- [2026-10-30] decision | **Fullscreen study mode = CSS theater mode, not the Fullscreen API** — rationale: iOS Safari lacks the API; overlay drops gutters/max-width; Escape exits fullscreen first then closes; evidence: commits `47b5709`, `0b5b963`.
- [2026-10-30] decision | **PPTX viewer container is the scroller** (`overflow-y-auto` + passed as the renderer's `scrollContainer` so both observers root at the true scroll element) — fixes last-slide cutoff; verified headless at 3 viewports; evidence: commit `47b5709`.
- [2026-10-30] decision | **Living-docs governance adopted** — four roles (Constitution `AGENTS.md`, Map `docs/ARCHITECTURE.md`, Status `docs/STATUS.md`, History this file); `audit/` + `tasks/` become historical archives; evidence: this change.
