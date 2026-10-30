# ECC Loop Plan — apply ECC skills & agents across the codebase

ECC 2.2.3 installed (official clone @ 25278e7 → `~/.config/opencode/`, user-owned
`opencode.json` preserved). This session acts as the loop operator: each iteration
loads the relevant ECC skill(s), dispatches ECC agent personas via subagents, fixes,
verifies with the 105-test suite, and commits in batches. Loop runs until every lane
is closed.

## Invariants (must hold every iteration)

- Frontend API contract (`frontend/lib/api.ts`) — additive changes only.
- Live DB `backend/student_library.db` stays clean (12 tables, 4 resources).
- Backend command preserved: `PYTHONIOENCODING=utf-8 RATE_LIMIT_PER_MINUTE=100000
  venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
  (no --reload; manual restart needed after code changes).
- Tests green each round: `venv\Scripts\python.exe -m pytest tests/ -q --no-header
  -p no:cacheprovider` from `backend/` (PS exit code 1 even on green; read the
  "N passed" line).
- No breaking changes; admin creds unchanged.

## Lane map (ECC skill → agent → targets)

| Lane | ECC skills | ECC agent persona | Targets (findings) |
|------|-----------|-------------------|--------------------|
| L1 API correctness & review | api-design, coding-standards, change-impact | code-reviewer, python-reviewer | H3, M15 (envelopes), M17, M5 (pagination parts), M6, M9, M16 |
| L2 Database & admin safety | database-migrations, error-handling | database-reviewer | H2 (hard cascade), H4 (N+1), H5 (bulk delete), M16 (audit/deleted_at) |
| L3 Security | security-review | security-reviewer | H3 leak class recheck, authz pass over admin routers, dependency audit (M14) |
| L4 Reliability | error-handling, verification-loop | build-error-resolver | M10 (SMTP timeout/socket leak), M12 residual (backup msg ids), M5 race |
| L5 Tests (TDD) | tdd-workflow, python-testing | tdd-guide | regression test per fix above; keep 105+ green |
| L6 Docs & deployment | deployment-patterns, docker-patterns, docs-governance | doc-updater | update docs/backend.md, CI health, Docker review |
| L7 Frontend (contract-guarded) | frontend-patterns, api-design | code-reviewer | verify contract unaffected; additive-only if gaps found |

## Iteration order

1. **Iter 1 (L1+L2 core)**: H2, H3, H4, H5 — the four open High findings. TDD each.
2. **Iter 2 (L4)**: M5, M6, M9, M10, M12-residual, M16.
3. **Iter 3 (L1)**: M15 (unify pagination envelopes), M17 (list/detail is_active).
4. **Iter 4 (L3)**: security-reviewer pass over admin surface + deps (closes M14 decision), dependency CVE scan.
5. **Iter 5 (L6+L7)**: docs refresh, CI/Docker review, frontend contract verification.
6. **Loop exit**: findings.md all closed or explicitly owner-deferred; full suite green; servers restarted on final code; smoke pass.

## Progress log

- [x] ECC installed & verified (312 skills / 103 commands; catalog live in harness)
- [x] Servers restored after harness restart (backend 8000 healthy, frontend 3000 OK)
- [x] Iter 1 (L1+L2): H2, H3, H4, H5, M9, M16, M17 fixed — commits `cce7296` + `e72ac12`; 118 tests green; live smoke pass
- [x] Iter 2 (L4): M5 (soft-delete filter + atomic pending write), M6 (409 on resolved), M10 (SMTP timeout + context manager), M12-residual (backup ids persisted) — `test_reliability_iter2.py`, 125 tests green; M18 ("branranch") retracted as tool-display false positive
- [x] Iter 3 (L1): M15 pagination unification — single envelope everywhere, `pages=ceil` (0 when empty), /history + /trusted enveloped; commit + live smoke pass; 134 tests green
- [x] Iter 4 (L3): security pass over admin surface + dependency audit (M14) — authz/CORS/role-vocab verified clean; audit-failure policy unified (3 wraps + 3 tests); M14 ledger row updated to fixed; 137 tests green
- [x] Iter 5 (L6+L7): docs refresh (backend.md invariants 6–7 + residual gaps pruned; API.md pagination-envelope section), CI/Docker review (already reality-based: dev deps excluded from image, image-build gate in CI, non-root + healthcheck — no changes needed), frontend contract verified (zero frontend diff across iters 1–4)
- [x] Loop exit (Iter 6): **COMPLETE** — 33/33 findings closed or owner-deferred (C4 Atlas credential + H10 password rotation are the only outstanding items, both owner actions on git-history secrets); final suite 137 passed; final smoke green (health 200, public stats, both listeners up); backend running iter-4 code, docs current
