# Project Status

> Current health, open owner actions, and the delete-zone. Structure: `docs/ARCHITECTURE.md`.
> Rules: `AGENTS.md`. Decisions: `docs/DECISIONS.md`.

**Last verified: 2026-10-30** (preview overhaul + fullscreen fix, headless-browser verified at 1440/768/375).

## Current state

- **Pre-launch.** No live student community; runs locally or in test deployments (`PRODUCT.md` owns positioning).
- Backend (:8000) and frontend (:3000) healthy; health endpoints and resource pages return 200.
- Test suite: **166 passed** (2026-11-05). CI runs the same reality-based suite.
- Security: 22 confirmed findings fixed + 2 backend dependency CVEs fixed; runtime re-probed (`audit/security-report.md`).
- Preview: **9 formats** render client-side (PDF, DOCX, PPTX, XLSX, TXT, MD, JPG, PNG, ZIP→listing) with a fullscreen study mode; PPTX last-slide scroll verified fixed on all viewports.
- Upgrade campaign: all 33 audit findings closed or owner-deferred (`tasks/findings.md`, loop complete `a91aaca`).

## Open owner actions (cannot be fixed by code)

| # | Action | Why | Source |
|---|---|---|---|
| 1 | **Rotate the MongoDB Atlas credential** (`f2l1@cluster0` cluster) | Baked into deleted scripts; lives in git history (local **and** origin) — assume compromised | `tasks/findings.md` C4 |
| 2 | **Rotate the exposed password (`Rajesh123%`) and assume those accounts compromised** | Real user credential in deleted scripts; history retains it | `tasks/findings.md` H10 |
| 3 | **Upgrade frontend dependencies** (next, zod, postcss) — need major version upgrades | Known vulnerabilities; blocked on major upgrades | `audit/security-report.md` |
| 4 | Review the 9 needs-validation / process items in the security report | Requires owner sign-off, not mechanical fixes | `audit/security-report.md` |
| 5 | **Add a LICENSE file** (README previously claimed MIT without one) | License is a legal commitment only the owner can make | README "License" section |

Deleting files or rewriting history here does **not** close #1/#2 — only rotating the actual credentials does.

## Known limitations (by design)

- **Single process.** In-memory rate limiting, lockout, reset tokens, view tracking, StatsEngine. Never scale workers (`docs/backend.md` owns the invariants).
- SQLite + Telegram-channel blob storage: zero infrastructure, single-container deploy (`PRODUCT.md` binding).
- 50 MB upload cap; password-reset token store is in-memory (single-process design).
- Moderation is **auto-approval on** by default (configurable) — owner may toggle at launch.

## Delete-zone (intentionally removed — do not recreate)

| Path / concept | Why removed | Replacement | Revisit condition |
|---|---|---|---|
| `scripts/*` — 13 dead Mongo/Beanie scripts (`check_courses.py`, `clear_resources.py`, `reset_password*.py`, `promote_admin.py`, …) | Unrunnable; several had live credentials baked in; `clear_resources.py` could wipe a remote DB unconditionally | None needed — ops via Alembic + the app itself | Only via a new decision entry in `docs/DECISIONS.md`; never restore scripts containing credentials |
| Deps: `redis`, `python-magic`, `sentry-sdk` (backend requirements) | Grep-verified unused | — | Re-add only if a feature genuinely adopts them |
| 500 MB in-memory `FileCache` (`services/cache.py`) | Dead code; disk LRU cache in `download_manager` is the real cache | `services/download_manager.py` disk cache | New decision entry only |
| `telegram.download_file` / `stream_file` and `download_manager` streaming dead paths | Dead code; blocking in async paths | Current to_thread-based paths | New decision entry only |
| `admin_dashboard_full` cache key | Zero consumers; wasted ~40k queries/day from a 15s refresh loop | — | — |
| Postgres-flavored `alembic/versions/001_initial.py` | Targeted PostgreSQL while the app runs SQLite; crashed on import | Metadata-driven SQLite migration (C2/C3 fixed) | — |
| CI fake services (Postgres + Redis) and missing `Dockerfile.prod` refs | Fictional pipeline | Reality-based ci.yml (SQLite tests, image-build validation) | — |
| Previous PPTX preview renderer (`pptx-preview`) | Superseded | `@aiden0z/pptx-renderer` 1.4.0 (commit `dcce22f`) | Only if it demonstrably fails a need the new renderer covers |

Anything deleted here stays deleted until a **new dated entry** in `docs/DECISIONS.md` records the reversal.
