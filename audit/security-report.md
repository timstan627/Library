# Security Audit — Student Resource Library

**Date:** 2026-10-28 · **Scope:** backend (FastAPI + Telegram storage) + frontend (Next.js 14) · **Method:** three parallel source reviews (authz/IDOR, upload pipeline, injection/config) → manual verification of every candidate → loopback runtime probes with disposable principals → fixes → re-probe.

**Principals used in probes:** one temp student account (`sec-probe-*@example.com`) and its uploaded file, both removed after each run. No real user data touched; DB end-state verified (1 user, 4 live resources, preserved review intact).

---

## Executive summary

| Verdict | Count |
|---|---|
| Confirmed findings **fixed** (backend + frontend) | 22 |
| Dependency vulnerabilities **fixed** (backend) | 2 (python-multipart, python-jose) |
| Dependency vulnerabilities **remaining** (frontend, need major upgrades) | 3 (next, zod, postcss) |
| Needs-validation / process items | 9 |
| Areas verified safe (evidence below) | 14 |

The most serious issue: **moderation was advisory, not enforced**. A student's public upload sits in `pending`; the file endpoints ignored `moderation_status` entirely, so anyone who knew (or guessed) the ID could download a not-yet-approved **or moderator-rejected** file, list it in the public feed, and — because the served content type was the *client-declared* one — serve attacker-chosen `text/html` inline (stored XSS). All confirmed at runtime, all fixed, re-verified.

---

## Runtime probe evidence (before → after)

| Probe (loopback, disposable principals) | Before | After |
|---|---|---|
| Anonymous GET of a **pending** resource by ID | `200` + metadata | **`404`** |
| Anonymous **download** of pending file bytes | `200` + bytes | **`404`** |
| Anonymous **preview** of pending file | `200` · `content-type: text/html` · `inline` | **`404`** |
| Pending item in public `/resources/` list | `true` | **`false`** |
| Refresh with a **fresh** refresh token after account ban | `200` + new tokens | **`401`** (session revoked) |
| Old **access** token after ban on required-auth endpoints | `403` (already rejected) | `403` |
| Old access token on **optional-auth** read endpoints | `200` (banned user acted as themselves) | `200` as **anonymous** |
| CORS: `Origin: https://evil.example` on error paths | origin echoed + credentials | **no echo** |
| CORS: allowed origin (`localhost:3000`) on error paths | echoed | still echoed |
| python-jose 3.3.0 with empty `JWT_SECRET_KEY` | empty-key HS256 encode **and** decode both succeed → forgeable tokens | startup refuses (prod) / random dev secret |
| Public list still shows approved content | 3 items | 3 items (no false positives) |

---

## Fixed findings

### HIGH

**F1/F2/F3 — Unapproved content readable, downloadable, listed publicly.**
`app/api/v1/resources.py` — `preview`, `download`, `preview-text`, `get_resource`, `get_resource_by_slug`, `list_resources` loaded resources with only `is_deleted == False` and checked visibility, never `moderation_status` (search.py already filtered it — the inconsistency is what made this exploitable). **Fix:** shared gate `_ensure_viewable()` — non-approved resources 404 for everyone except owner and moderators; visibility check preserved on top; `list_resources` adds `moderation_status == "approved"` for all non-owner paths. Re-verified by probe (table above).

**F3 (stored XSS half) — client-controlled MIME served inline.**
Upload stored `file.content_type` verbatim and `/preview` served it as the `FileResponse` media type with `inline` disposition. A `.txt` uploaded with `Content-Type: text/html` rendered as HTML in the browser (probe-confirmed). **Fix:** MIME derived server-side via `mimetypes.guess_type(filename)` (extension allowlist still gates which extensions exist); `Content-Disposition` built by `_content_disposition()` — control chars/CR/LF/quotes stripped (header injection), RFC 5987 UTF-8 parameter with ASCII fallback (previously a unicode filename returned 500).

**F4 — private→public moderation bypass.**
Private uploads are auto-approved (owner-only, sane). `update_resource` let the owner flip visibility to `public`/`unlisted` while keeping the auto-approved status — publishing arbitrary content with zero moderation. **Fix:** non-moderator visibility changes out of `private` reset `moderation_status` to `pending`.

**F5 — refresh issued tokens to banned users.**
`/auth/refresh` verified the JWT and the session row but **never loaded the user** (probe-confirmed: banned user refreshed a fresh token → 200 + new pair). **Fix:** refresh loads the user; banned/inactive → 401 and the session is revoked. Re-verified: 401.

**F15 — empty JWT secret = forgeable tokens.**
config.py's comment claimed SecurityManager replaces empty secrets with a random one — no such code existed. Local test: `jwt.encode(..., '')` and `jwt.decode(..., '')` both succeed on python-jose 3.3.0, so a deployment that forgot `JWT_SECRET_KEY` accepted attacker-minted admin tokens. **Fix:** `_ensure_runtime_secrets()` runs at import of `app.core.security` — empty values in development become a process-local random secret (warned), in production startup **raises**. The config comment is now true.

**F14 — hardcoded admin credentials in source.**
`database.py` seeded `blasteranna1414@gmail.com` / `Blaster1414&` on any empty database. **Fix:** bootstrap strictly from `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`; skips with a warning in dev, hard-fails in production. (Existing local DB unaffected.)

**F16 — Telegram bot commands bound to a hardcoded owner ID.**
`telegram.py` fell back to `5422016608` when `TELEGRAM_OWNER_ID` was unset — and the handlers include **DB backup, DB send and DB replace** commands. **Fix:** no fallback; without configured owner the command handlers are not registered at all.

### MEDIUM

**F6 — banned users on optional-auth endpoints.** `get_current_user` returned the banned user (required dep already 403'd). Now returns `None` → treated as anonymous everywhere. Probe-verified.

**F7/F8 — ratings on private/pending resources + self-rating.** Anyone could rate (and surface review text on) unapproved resources, and an uploader could rate their own file. **Fix:** create requires approved + not own resource; listing gated the same way (owner/mod can still see). Also fixed the email-prefix leak in reviewer display names (`Student` fallback instead of email local-part).

**F9 — reset tokens logged & stored plaintext.** `password_reset.py` logged the raw token (line 50-51) and kept it in a module dict in cleartext. **Fix:** log line removed (email is the delivery channel); dict keyed by SHA-256 digest.

**F12 — rate-limit identity trusted client headers.** The limiter keyed on `X-Forwarded-For` implicitly (via login) / direct IP — behind nginx every request shares one bucket; accepting the header blindly lets a client spin fresh buckets or lock out a victim's IP. **Fix:** `get_client_ip()` — forwarded headers honored **only** when the direct peer is in `TRUSTED_PROXIES` (default loopback), used by both the login limiter and the global rate limiter.

**F13 — CORS reflection on error paths.** `HTTPException` and global exception handlers echoed any `Origin` with `Allow-Credentials: true` (the CORS middleware doesn't run there). **Fix:** `_cors_headers_for()` echoes only origins on the allowlist. Probe-verified both directions.

**F17 — moderators couldn't moderate.** Every endpoint in `admin/moderation.py` used `require_admin`, so the moderator role was decorative. **Fix:** `require_moderator` (admin + moderator).

**F21 — vulnerable Python dependencies.** `python-multipart 0.0.9` (CVE-2024-24762 ReDoS — unauthenticated DoS via multipart parse) → **0.0.20**; `python-jose 3.3.0` (CVE-2024-33663/33664, plus the empty-key behavior above) → **3.4.0**. Installed and app-import verified.

### LOW

**F10 — reset/ban lifecycle gaps.** Reset confirm now re-checks `is_banned`; password **change** and password **reset** both revoke all of the user's sessions (previously a stolen session survived a password change indefinitely).

**F11 — upload hardening.** Size enforced during a chunked read (answers **413**, no whole-file RAM spike); visibility/password validation moved **before** the Telegram upload so rejected requests can't leave orphaned files in the channel.

**F18 — dead legacy router deleted.** `backend/app/api/v1/admin.py` was shadowed by the `admin/` package (Python prefers packages) and **unmounted** — but it contained a `list_users` returning password hashes and ban/clear-all-data endpoints. Deleted (`git rm`), so it can never be accidentally re-mounted.

**F19/F20 — rating hygiene.** Review-only rows no longer corrupt aggregates on delete (counter drift); display-name fallback no longer leaks email prefixes.

**F22 — open redirect + MFA brute force.** `returnUrl` now rejects protocol-relative `//evil.com`; failed MFA attempts consume the same login lockout budget (`auth_rate_limiter`), so the TOTP challenge can't be brute-forced around the limiter.

---

## Dependencies

| Package | Was | Now | Note |
|---|---|---|---|
| python-multipart | 0.0.9 | **0.0.20** | CVE-2024-24762 (ReDoS, unauth DoS) |
| python-jose | 3.3.0 | **3.4.0** | CVE-2024-33663/33664 + empty-key tokens |
| axios (frontend) | 1.13.2 | **1.19.x** via `npm audit fix` | SSRF/CRLF/prototype-pollution advisory chain cleared |
| next (frontend) | 14.2.35 | **needs upgrade** | critical: GHSA-p293-qw3h-jr36 (Windows RCE), GHSA-2xp9-vwfh-vxw4 + GHSA-2464-fhr4-w9xw (image-optimizer RCEs) — fix ≥ 15.5.24 / 16.4.3 |
| zod (frontend) | 3.25.76 | **needs upgrade** | high GHSA-mrhx-c7xc-m3w5; fix is 4.x (breaking) |
| postcss (via next 14) | 8.4.x | **needs upgrade** | high; resolved by the Next upgrade |

`npm audit fix` (non-breaking) applied cleanly (lockfile-only); the remaining three require major-version upgrades — see N1.

---

## Needs-validation / process items (not code bugs)

- **N1 (HIGH) — Next.js upgrade.** `next ≥ 15.5.24` (or 16.4.3) closes the critical RCE advisories. Needs a planned migration (Next 15/16 + React 19, ESLint config changes); the app must never be internet-facing on 14.2.35.
- **N2 (HIGH) — secret/credential rotation.** `backend/.env` **was tracked in git** with live values (Telegram bot token + API hash, JWT/SECRET/HMAC keys, DB URI, and the admin password that was also hardcoded). It is now untracked and ignored — but the values live in git history. **Rotate everything** (bot token via @BotFather, API hash, all three signing keys, DB credentials, admin password). Run BFG/history rewrite only if this repo was ever pushed anywhere.
- **N3 — DEBUG=true in the dev `.env`** mounts `/docs`, `/openapi.json`, `/metrics` and (with admin auth) system endpoints like clear-all-data. Fine locally; document that production must set `DEBUG=false` (config default is now false).
- **N4 — registration enumeration.** `/auth/register` answers "Email already registered" (400). Uniform response (always 201 + email notice) would hide account existence; accepted for now as a UX trade-off.
- **N5 — quota TOCTOU.** Parallel uploads can race `storage_used_bytes` before it's persisted. Consequence is bounded (default quota is effectively unlimited); switch to a locked UPDATE if quotas become real.
- **N6 — backups and user files share one Telegram channel.** The scheduled DB backup + bot DB-send flows ship the SQLite DB to the same channel that stores user files; anyone with bot access gets both. Prefer a separate channel + scoped access.
- **N7 — bcrypt 72-byte truncation.** passlib/bcrypt silently truncates >72 bytes; max-length is 100 for account passwords (and free-form for resource passwords). Low real-world risk; note for documentation.
- **N8 — resource password in URL query** (`/preview?password=...`, `/download?password=...`). Ends up in logs/browser history. A POST-based unlock form would be cleaner; brute force of the password itself is rate-limited by the global limiter.
- **N9 — bearer tokens in `localStorage`** (frontend). Standard trade-off for this architecture; XSS is the main escalation path, and the stored-XSS vector above is closed. CSP still allows `unsafe-inline` styles/scripts (needed by Next dev; revisit at the Next upgrade).

---

## Verified safe

With source evidence from the three review passes:

1. **SQL injection — none.** All queries via SQLAlchemy ORM; `sort_by` whitelisted in `search.py`.
2. **SSRF — none.** No user-supplied URL is ever fetched server-side.
3. **Path traversal — none.** Files never touch disk paths derived from user input (Telegram storage + hash-keyed cache).
4. **Library collections fully owner-scoped** (`user_id` checked on every GET/PUT/DELETE/add/remove).
5. **Reports owner/mod-gated** — users see only their own; resolution state not spoofable.
6. **Admin surface fully gated** — every endpoint in the mounted `admin/` package carries an explicit role dependency.
7. **Passwords:** bcrypt cost 12; login errors uniform ("Invalid email or password").
8. **Refresh tokens:** rotated on every use, stored as SHA-256 session hashes; logout revokes server-side.
9. **MFA:** login returns empty token pair until TOTP verifies; setup/disable both require a live code (now lockout-protected).
10. **Duplicate detection scoped per user** — no cross-user content disclosure via dedup.
11. **Frontend XSS sinks — none** (no `dangerouslySetInnerHTML`/`eval`/`innerHTML`).
12. **Security headers on every response:** `nosniff`, `frame-ancestors 'none'`, Referrer-Policy, Permissions-Policy; HSTS in production.
13. **Legacy unmounted admin router (password-hash exposure) — deleted**, not just ignored.
14. **Login lockout** — 5 failures / 15 min per IP+email (trusted-proxy aware), MFA failures included.

---

## Files changed (this audit)

**Backend:** `app/api/v1/resources.py`, `ratings.py`, `deps.py`, `auth.py`, `users.py`, `password_reset.py`, `app/api/v1/admin.py` (deleted), `app/api/v1/admin/moderation.py`, `app/core/security.py`, `app/core/database.py`, `app/core/middleware.py`, `app/core/config.py`, `app/main.py`, `app/services/telegram.py`, `requirements.txt`.
**Frontend:** `app/auth/login/page.tsx`, `app/resources/[slug]/page.tsx` (axios typing), `package-lock.json`.
**Repo hygiene:** `.gitignore` (+`.env`), `backend/.env` untracked (git history retains old values — see N2).

## Verification

Backend re-probed after restart (all closes in the table above); `import app.main` clean; frontend `tsc --noEmit` clean; login/home/browse pages compile and serve 200; `npm audit --omit=dev` reduced from 8 (1 critical, 6 high) to 3 (all requiring the planned major upgrades).
