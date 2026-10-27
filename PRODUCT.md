# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Students** in an open, self-registering community (no single institution): they upload and share notes, assignments, exam papers, and other study materials; browse and search by department, course, semester, and tags; preview or download files; and rate and review resources. **Owners/admins** (also students) operate the platform: moderation, department/course management, user roles, report handling, and system health. Status today: **pre-launch** — the platform runs locally or in test deployments only; there is no live student community yet.

## Product Purpose

A free, community-run library where students share study materials without gatekeeping or storage limits. It exists because useful study files get lost in chats and silos; this gives them a permanent, searchable, structured home. Success means students can find and trust the material they need in seconds, contributors keep uploading because the flow is frictionless, and a small student team can operate the whole thing without infrastructure spend.

## Positioning

Unlimited storage at zero cost — files live in Telegram channels via the Telegram API, so the platform never pays for or provisions file storage, and it deploys with zero external dependencies (SQLite, in-memory cache, single Docker container). A conventional file-sharing or course-hub product cannot truthfully copy "unlimited, free, self-hosted-in-one-container" without adopting the same mechanism.

## Operating Context

- Students register → upload → (configurable moderation) → resources go live for browse/search/download; PDFs and images preview inline in the browser.
- Admins work in a dashboard: approve/reject/flag resources, CRUD departments and courses, assign roles (student/moderator/admin), ban users, resolve reports, bulk-delete, and monitor Telegram API, cache, and database health.
- Deployment is a single Docker container behind an Nginx reverse proxy; the backend stores file content in Telegram channels, so an operational Telegram bot + channel configuration is part of running the product.
- Legal pages (DMCA, Privacy, Terms) are part of the operating surface, reflecting a real copyright-compliance posture for user-uploaded academic material.

## Capabilities and Constraints

- Upload/share, full-text search with filters, inline preview (PDF/images), star ratings with comments, user profile with usage stats, optional password-protected files.
- Auth: JWT access+refresh (24h/30d), optional TOTP MFA; per-IP rate limiting (default 60 req/min).
- Roles: student / moderator / admin. Resource moderation exists but **auto-approval is enabled by default** (configurable).
- Hard limits: 50 MB per file; allowed formats PDF, DOCX, PPTX, XLSX, ZIP, TXT, MD, JPG, PNG; per-user storage quota nominally unlimited.
- Storage depends on Telegram availability — without configured Telegram API credentials and a channel, file upload/storage does not work.
- Deliberately undecided: final product name (see Brand Commitments), launch timing, and any accessibility standard beyond good practice.

## Brand Commitments

- **Student-run ethos is binding:** "Built with ❤️ for students, by students" — a community, free-access positioning that design and copy must respect.
- **Compliance posture is binding:** the DMCA/privacy/terms presence reflects a real legal commitment for user-uploaded material, not decorative copy.
- **Telegram storage is binding** as an architectural commitment, not an implementation detail.
- The product name is **explicitly flexible**: future design work may rename it; nothing else (logo, tagline) exists yet as a fixed asset.

## Evidence on Hand

- Complete repository documentation: `README.md`, `docs/USER_GUIDE.md`, `docs/OWNER_GUIDE.md`, `docs/API.md`, `docs/DEPLOYMENT.md`, `TELEGRAM_AND_DATABASE_GUIDE.md` — thorough operational truth, no marketing claims.
- A working full-stack implementation (Next.js 14 app with ~26 routes, FastAPI backend) that runs locally.
- **Pre-launch: no real users, content, testimonials, usage metrics, or press exist. Future work must not fabricate any of these.**

## Product Principles

1. **Free access, zero friction.** Nothing about finding or sharing material should cost students money or patience; free storage and self-serve upload are the point, not features.
2. **Trust is designed, not assumed.** Ratings, moderation, reports, and real legal pages are load-bearing; the community's willingness to rely on strangers' notes depends on them being first-class.
3. **Students can run it.** Zero-config database, one-container deploy, in-app health monitoring — the operator is a student volunteer, not a DevOps team; every operational surface should stay that simple.
4. **Honesty over inflation.** Pre-launch truth: show real states, real counts, and real empty states; never invented numbers or fake social proof.
5. **Academic structure is the map.** Departments, courses, and semesters are how students actually think; organization should follow their mental model, not a generic file listing.
