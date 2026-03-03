# 🛡️ Owner / Admin Guide — Student Resource Library

> Complete reference for administrators and owners managing the Student Resource Library platform.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Environment Configuration](#environment-configuration)  
3. [Admin Dashboard](#admin-dashboard)
4. [Department Management](#department-management)
5. [Course Management](#course-management)
6. [Resource Moderation](#resource-moderation)
7. [User Management](#user-management)
8. [Report Handling](#report-handling)
9. [System Health & Monitoring](#system-health--monitoring)
10. [API Administration](#api-administration)
11. [Backup & Recovery](#backup--recovery)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Admin Panel

1. Log in with an account that has `admin` or `moderator` role
2. Navigate to **Profile → Admin** or go directly to `/admin`
3. Non-admin users will see a **403 Forbidden** page

### Role Hierarchy

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: manage users, roles, resources, departments, courses, reports, system settings, bulk operations, data clear |
| **Moderator** | Moderate resources (approve/reject), view dashboard stats, handle reports |
| **Student** | Upload, download, browse, rate, and report resources |

### First-Time Setup

1. **Register** your account at `/auth/register`
2. **Promote to admin** — run the following SQL against the SQLite database:
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
   ```
   Or use the API:
   ```bash
   # After logging in and getting a token
   curl -X PUT "http://localhost:8000/api/v1/admin/users/{user_id}/role?role=admin" \
     -H "Authorization: Bearer <your_token>"
   ```
3. Set up **Departments** and **Courses** from the admin panel

---

## Environment Configuration

All configuration is managed via environment variables (loaded from `.env` file in the backend directory).

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Student Resource Library` | Application name |
| `APP_URL` | `http://127.0.0.1:3000` | Frontend URL |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `DEBUG` | `true` | Enables Swagger docs at `/docs`, Prometheus at `/metrics` |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-this-in-production` | Application secret key |
| `JWT_SECRET_KEY` | `change-this-jwt-secret` | JWT token signing key |
| `HMAC_SECRET_KEY` | `change-this-hmac-secret` | HMAC verification key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |

> ⚠️ **CRITICAL**: Change all secret keys in production! Generate with `openssl rand -hex 32`

### Telegram File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_API_ID` | — | Telegram API ID (get from [my.telegram.org](https://my.telegram.org)) |
| `TELEGRAM_API_HASH` | — | Telegram API hash |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_PRIMARY_CHANNEL` | — | Channel ID for file storage (negative number) |
| `TELEGRAM_BACKUP_CHANNEL` | — | Backup channel ID |
| `TELEGRAM_OWNER_ID` | — | Your Telegram user ID |

#### Setting Up Telegram Storage

1. Create a **Telegram Bot** via [@BotFather](https://t.me/BotFather) — save the token
2. Get your **API ID** and **Hash** from [my.telegram.org](https://my.telegram.org/apps)
3. Create a **private channel** in Telegram for file storage
4. Add your **bot as admin** to the channel
5. Get the **channel ID** (forward a message from channel to [@userinfobot](https://t.me/userinfobot), the ID will be a negative number like `-1002284190309`)
6. Set all values in `.env`

### Email (SMTP)

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password or app password |
| `EMAILS_FROM_EMAIL` | — | Sender email address |
| `EMAILS_FROM_NAME` | `Student Library` | Sender display name |

### File Upload Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE_MB` | `50` | Maximum file size per upload |
| `STORAGE_QUOTA_MB` | `104857600` (~100 TB) | Per-user storage quota |
| `ALLOWED_EXTENSIONS` | `pdf,docx,pptx,xlsx,zip,txt,md,jpg,png` | Allowed file types |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MFA` | `true` | Enable two-factor authentication |
| `ENABLE_RATE_LIMITING` | `true` | Enable request rate limiting |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max requests per minute per IP |
| `ENABLE_SENTRY` | `false` | Enable Sentry error tracking |
| `SENTRY_DSN` | — | Sentry DSN URL |

---

## Admin Dashboard

**URL**: `/admin`

The dashboard displays real-time platform statistics:

### Statistics Cards
- **Total Users** — registered accounts with weekly growth indicator
- **Total Resources** — all uploaded files with weekly growth
- **Downloads** — aggregate download count
- **Storage Usage** — total file storage consumed

### Management Hub

Quick access cards to admin sub-sections:

| Section | URL | Description |
|---------|-----|-------------|
| **Resources** | `/admin/resources` | View, search, delete all uploaded resources |
| **Departments** | `/admin/departments` | Create, edit, delete academic departments |
| **Courses** | `/admin/courses` | Create, edit, delete courses under departments |
| **Moderation** | `/admin/moderation` | Approve or reject pending resources |
| **Users** | `/admin/users` | Manage user accounts, roles, bans |

### System Health

Shows status indicators for:
- **Telegram API** — connection to Telegram storage
- **In-Memory Cache** — application cache status
- **SQLite DB** — database connectivity

---

## Department Management

**URL**: `/admin/departments`

### Creating a Department

1. Click **+ New Department**
2. Fill in:
   - **Name** (required) — e.g., "Computer Science"
   - **Code** (required) — e.g., "CSE" (unique, uppercase)
   - **Description** (optional)
3. Click **Create**

### Editing a Department

1. Click the **pencil icon** (✏️) on the department row
2. Modify fields
3. Click **Update**

### Deleting a Department

1. Click the **trash icon** (🗑️) on the department row
2. Confirm the deletion

> ⚠️ Deleting a department does **not** delete its courses or resources. Unlink courses first.

### Department Table Columns
- **Department** — Name and code
- **Courses** — Number of active courses
- **Status** — Active/Inactive toggle
- **Actions** — Edit, Delete

---

## Course Management

**URL**: `/admin/courses`

### Creating a Course

1. Click **+ New Course**
2. Fill in:
   - **Course Code** (required) — e.g., "CS101" (unique)
   - **Course Name** (required) — e.g., "Data Structures"
   - **Department** (required) — select from dropdown
   - **Semester** (optional) — e.g., "1st Semester"
   - **Description** (optional)
3. Click **Create**

### Editing & Deleting

Same flow as departments — use the action icons on each course row.

### Course Table Columns
- **Code** — Unique course code
- **Course Name**
- **Department** — Parent department
- **Resources** — Number of uploaded resources
- **Status** — Active/Inactive
- **Actions** — Edit, Delete

---

## Resource Moderation

**URL**: `/admin/moderation`

### Moderation Queue

All newly uploaded resources enter the moderation queue (unless auto-approval is enabled).

| Status | Description |
|--------|-------------|
| `pending` | Awaiting moderator review |
| `approved` | Visible to all users |
| `rejected` | Hidden from public, uploader notified |

### Reviewing a Resource

1. View the resource details (title, uploader, file type, size)
2. Click **Approve** ✅ to make it public
3. Click **Reject** ❌ to hide it (optionally provide a reason)

### Resource Management

**URL**: `/admin/resources`

Full resource management with:
- **Search** by title or course code
- **Delete** individual resources
- **Bulk Delete** — select multiple resources and delete
- **Permanent Delete** — removes from both database and Telegram storage

---

## User Management

### Admin API Endpoints

| Action | Method | Endpoint |
|--------|--------|----------|
| List users | `GET` | `/api/v1/admin/users` |
| Update role | `PUT` | `/api/v1/admin/users/{id}/role?role=admin` |
| Ban user | `POST` | `/api/v1/admin/users/{id}/ban?reason=...` |
| Unban user | `POST` | `/api/v1/admin/users/{id}/unban` |

### Roles
- `student` — default role for new users
- `moderator` — can moderate resources and handle reports
- `admin` — full system access

### Banning a User

1. Find the user by email or username
2. Ban with a **mandatory reason** (min 5 characters)
3. Banned users:
   - Cannot log in
   - Existing sessions are invalidated
   - Resources remain visible but cannot upload new ones

### Unbanning a User

Simply unban — the user can log in again immediately.

---

## Report Handling

### Report Statuses

| Status | Description |
|--------|-------------|
| `pending` | New report, awaiting review |
| `reviewing` | Under investigation |
| `resolved` | Action taken, case closed |
| `dismissed` | Report deemed invalid |

### Workflow

1. Users submit reports from the **resource detail page** → "Report" button
2. Reports appear in the admin dashboard
3. Moderators review and update status
4. Optionally add resolution notes

### API

```
GET  /api/v1/admin/reports              — List all reports
PUT  /api/v1/admin/reports/{id}?status=resolved  — Update status
```

---

## System Health & Monitoring

### Health Check

```bash
curl http://localhost:8000/health
# Returns: {"status": "ok"}
```

### Prometheus Metrics

When `DEBUG=true`, metrics are available at:
```
http://localhost:8000/metrics
```

### API Documentation (Swagger)

When `DEBUG=true`:
```
http://localhost:8000/docs
```

### Request Timing

All requests are timed via middleware. Check backend logs for performance data:
```
2026-03-03 10:00:00 - Request to /api/v1/resources took 45ms
```

---

## API Administration

### Dangerous Operations

These operations require admin role and explicit confirmation:

#### Clear All Data
```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/clear-all?confirm=CONFIRM_DELETE_ALL" \
  -H "Authorization: Bearer <admin_token>"
```
> ⚠️ **This permanently deletes ALL resources from database and Telegram. Cannot be undone.**

#### Bulk Delete Resources
```bash
curl -X POST "http://localhost:8000/api/v1/admin/resources/bulk-delete" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '["resource_id_1", "resource_id_2"]'
```

#### Database Statistics
```bash
curl "http://localhost:8000/api/v1/admin/db-stats" \
  -H "Authorization: Bearer <admin_token>"
```

Returns table sizes, row counts, and database file size.

---

## Backup & Recovery

### SQLite Database Backup

The SQLite database file is located at `backend/student_library.db`.

```bash
# Simple file copy backup
cp backend/student_library.db backup/student_library_$(date +%Y%m%d).db

# Or using SQLite's built-in backup
sqlite3 backend/student_library.db ".backup 'backup/student_library_backup.db'"
```

### File Storage

All uploaded files are stored in **Telegram channels**. They persist in Telegram independently of the application server. No file backup is needed beyond maintaining the Telegram channel.

### Recovery

1. Restore the SQLite database file
2. Restart the backend server
3. All file download links (Telegram message IDs) are stored in the DB and will resume working

---

## Deployment

### Local Development

```bash
# Terminal 1: Backend
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Docker (Production)

```bash
# Build
docker build -t student-library .

# Run
docker run -p 80:80 \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32) \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -v ./data:/app/backend/data \
  student-library
```

The Docker container bundles:
- **Nginx** (port 80) — reverse proxy
- **Backend** (port 8000) — FastAPI
- **Frontend** (port 3000) — Next.js

### Koyeb / Cloud Deployment

1. Push code to GitHub
2. Connect to Koyeb → Docker deployment
3. Set environment variables in the Koyeb dashboard
4. Expose port **80**

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Can't access admin panel** | Verify your account has `admin` role in the database |
| **File upload fails** | Check Telegram bot token and channel permissions |
| **500 on department creation** | Ensure department code is unique |
| **Slow API responses** | Check SQLite file isn't locked; restart backend |
| **Login returns 401** | Token expired — refresh or re-login |
| **CORS errors** | Verify `APP_URL` matches your frontend URL |

### Logs

```bash
# Backend logs (development)
# Visible in terminal running uvicorn

# Docker logs
docker logs student-library -f

# Specific log level
LOG_LEVEL=debug python -m uvicorn app.main:app --log-level debug
```

### Database Reset

```bash
# Delete and recreate
rm backend/student_library.db
# Restart backend — tables auto-create on startup
```

---

## Quick Reference — Admin API Endpoints

| Category | Method | Endpoint | Auth |
|----------|--------|----------|------|
| Dashboard | `GET` | `/api/v1/admin/dashboard` | Moderator+ |
| DB Stats | `GET` | `/api/v1/admin/db-stats` | Admin |
| List Resources | `GET` | `/api/v1/admin/resources` | Moderator+ |
| Delete Resource | `DELETE` | `/api/v1/admin/resources/{id}` | Admin |
| Perm Delete | `DELETE` | `/api/v1/admin/resources/{id}/permanent` | Admin |
| Bulk Delete | `POST` | `/api/v1/admin/resources/bulk-delete` | Admin |
| Clear All | `DELETE` | `/api/v1/admin/clear-all` | Admin |
| List Users | `GET` | `/api/v1/admin/users` | Admin |
| Update Role | `PUT` | `/api/v1/admin/users/{id}/role` | Admin |
| Ban User | `POST` | `/api/v1/admin/users/{id}/ban` | Admin |
| Unban User | `POST` | `/api/v1/admin/users/{id}/unban` | Admin |
| List Reports | `GET` | `/api/v1/admin/reports` | Moderator+ |
| Update Report | `PUT` | `/api/v1/admin/reports/{id}` | Moderator+ |
| Departments | `CRUD` | `/api/v1/admin/departments` | Admin |
| Courses | `CRUD` | `/api/v1/admin/courses` | Admin |
| Moderation | `CRUD` | `/api/v1/admin/moderation` | Moderator+ |

---

<p align="center">
  For user-facing instructions, see <a href="USER_GUIDE.md">User Guide</a>.
</p>
