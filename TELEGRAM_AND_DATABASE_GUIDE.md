# 📡 Telegram Storage & Database Management Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Telegram as File Storage](#telegram-as-file-storage)
3. [Bot Commands](#bot-commands)
4. [File Upload Flow](#file-upload-flow)
5. [File Download Flow](#file-download-flow)
6. [Disk Cache System](#disk-cache-system)
7. [Database Management](#database-management)
8. [Database Resilience](#database-resilience)
9. [Backup & Recovery](#backup--recovery)
10. [Environment Configuration](#environment-configuration)
11. [Edge Cases & Error Handling](#edge-cases--error-handling)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Student Resource Library uses **Telegram channels as cloud file storage** and **SQLite as the database**. This eliminates the need for expensive cloud storage (S3, GCS) or external databases.

```
┌──────────────────────────────────────────────────────────────┐
│                    Student Resource Library                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │ Frontend │────▶│  Backend API │────▶│ Telegram Channel │  │
│  │ Next.js  │     │   FastAPI    │     │  (File Storage)  │  │
│  └──────────┘     └──────┬───────┘     └─────────────────┘  │
│                          │                                   │
│                   ┌──────┴───────┐                           │
│                   │    SQLite    │                           │
│                   │  (Metadata)  │                           │
│                   └──────────────┘                           │
│                                                              │
│  Key Components:                                             │
│  • telegram.py      → Pyrogram client (upload/download)     │
│  • download_manager → Disk cache + concurrency control      │
│  • database.py      → Auto-recovery + backup/restore        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### What's Stored Where?

| Data | Storage Location |
|------|-----------------|
| File content (PDF, PPTX, etc.) | Telegram Primary Channel |
| File backup copies | Telegram Backup Channel |
| Resource metadata (title, tags, course code) | SQLite `resources` table |
| User accounts, ratings, downloads | SQLite database |
| Recently downloaded files | Disk LRU Cache (`file_cache/` folder) |

---

## Telegram as File Storage

### Why Telegram?

- **Free unlimited storage** — Telegram allows up to 2GB per file
- **No monthly costs** — No S3/GCS bills
- **Built-in CDN** — Files are distributed across Telegram's global infrastructure
- **Redundancy** — Telegram stores multiple copies internally
- **API access** — Pyrogram library provides full async file operations

### How It Works

Telegram channels act as **file repositories**. Each uploaded file becomes a **message** in the channel. The application stores the `message_id` and `channel_id` in the SQLite database. When a user downloads a file, the backend retrieves it from Telegram using these IDs.

```
Upload: User → Backend → Telegram Channel → Returns message_id
                                                    │
                                              Saved in SQLite
                                                    │
Download: User ← Backend ← Telegram Channel ← Lookup message_id
```

### Channel Configuration

| Setting | Description | Env Variable |
|---------|-------------|-------------|
| Primary Channel | Main storage for all files | `TELEGRAM_PRIMARY_CHANNEL` |
| Backup Channel | Automatic backup copies | `TELEGRAM_BACKUP_CHANNEL` |
| Bot Token | The bot that manages files | `TELEGRAM_BOT_TOKEN` |
| API ID | Telegram API application ID | `TELEGRAM_API_ID` |
| API Hash | Telegram API application hash | `TELEGRAM_API_HASH` |
| Owner ID | Only owner can use bot commands | `TELEGRAM_OWNER_ID` |

> **Important:** The bot must be an **admin** in both the primary and backup channels with permission to post and delete messages.

---

## Bot Commands

The Telegram bot responds **only to the owner** (configured via `TELEGRAM_OWNER_ID`). Available commands:

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message and help | `/start` |
| `/help` | Show available commands | `/help` |
| `/search <query>` | Search resources by title, course code, or tags | `/search python` |
| `/get_<message_id>` | Download a specific file by its Telegram message ID | `/get_12345` |

### Search Example

```
You:  /search calculus

Bot:  📚 Found 3 resources:
      
      📄 Calculus I Notes
      CODE: MATH101
      SIZE: 2.3 MB
      ⬇️ /get_4567
      
      📄 Calculus Problems Set
      CODE: MATH102
      SIZE: 1.1 MB
      ⬇️ /get_4570
```

### Get File Example

```
You:  /get_4567

Bot:  ⬇️ Fetching file...
      [File: Calculus_I_Notes.pdf (2.3 MB)]
      📄 Calculus I Notes
      🔗 http://yoursite.com/resources/calculus-i-notes
```

The bot copies the file directly from the storage channel to your DM — no need to access the channel manually.

---

## File Upload Flow

When a user uploads a resource through the website:

```
Step 1: User selects file + fills metadata (title, course, tags)
            │
Step 2: Frontend sends multipart POST to /api/v1/resources/upload
            │
Step 3: Backend validates:
         ├── File extension allowed? (pdf, docx, pptx, xlsx, zip, txt, md, jpg, png)
         ├── File size ≤ 50MB?
         └── User's storage quota not exceeded?
            │
Step 4: Upload to Telegram Primary Channel
         ├── file_bytes → BytesIO stream
         ├── send_document() → Telegram API
         ├── Returns: { message_id, file_id, channel_id, file_size }
         └── FloodWait handling: auto-retry after cooldown period
            │
Step 5: Background: Upload copy to Backup Channel (non-blocking)
         └── asyncio.create_task(_backup_upload(...))
            │
Step 6: Save metadata to SQLite
         ├── title, course_code, tags, description
         ├── telegram_message_id (for future downloads)
         ├── telegram_channel_id
         ├── file_size, mime_type, file_extension
         └── uploader_id (linked to user)
            │
Step 7: Return resource data to frontend
```

### Rate Limiting

Telegram has strict rate limits. The upload process includes:
- **2-second delay** before each upload
- **1-second cooldown** after each upload
- **FloodWait auto-retry**: If Telegram returns a `FloodWait` error, the bot sleeps for the required duration and retries automatically

---

## File Download Flow

When a user clicks "Download" on the website:

```
Step 1: Frontend sends GET /api/v1/resources/{id}/download
            │
Step 2: Backend checks:
         ├── Resource exists and not deleted?
         ├── User has access? (visibility check)
         └── Password correct? (if password-protected)
            │
Step 3: DownloadManager.get_file() — Hybrid retrieval:
         │
         ├── Check DISK CACHE → file_cache/{channel}_{message}
         │   ├── HIT: Return cached file path instantly (0 latency)
         │   └── MISS: Continue to Telegram download
         │
         ├── Acquire SEMAPHORE slot (max 5 concurrent downloads)
         │   └── If all slots busy: wait in queue
         │
         ├── Double-check cache (may have been downloaded while waiting)
         │
         ├── Download from Telegram:
         │   ├── client.get_messages(channel_id, message_id)
         │   ├── Check: message exists? not deleted? has document?
         │   │   └── If missing → raise FileNotFoundInTelegram (→ 404)
         │   ├── client.download_media(message) → temp file
         │   └── Verify temp file exists and is not empty
         │
         ├── Cache to disk: copy temp file → file_cache/
         │   └── If file > 25% of cache max → skip caching
         │
         └── Return file path
            │
Step 4: Stream file to user via FileResponse
         └── Low memory: file served directly from disk (not RAM)
            │
Step 5: Log download + increment download counter
```

### Memory Efficiency

The old approach loaded entire files into RAM. The new hybrid approach:

| Metric | Old (RAM) | New (Disk Cache) |
|--------|-----------|------------------|
| Memory per download | Full file size | ~1MB (chunk buffer) |
| 10 users × 50MB file | 500MB RAM | ~10MB RAM |
| Repeated downloads | Re-download every time | Instant from cache |
| Concurrent limit | None (crashes under load) | 5 simultaneous |

---

## Disk Cache System

The `DownloadManager` maintains an LRU (Least Recently Used) disk cache to avoid repeated Telegram API calls.

### How It Works

```
file_cache/
├── -1002284190309_4567    ← channel_id + message_id
├── -1002284190309_4570
├── -1002284190309_4580
└── ... (auto-managed)
```

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Max cache size | 1 GB | Total disk space for cached files |
| Max file to cache | 25% of max | Individual file too large to cache |
| Concurrent downloads | 5 | Max simultaneous Telegram downloads |
| Chunk size | 1 MB | Streaming read buffer |
| Cooldown | 0.5s | Delay after each Telegram download |

### Cache Eviction

When the cache is full, the **least recently used** files are automatically deleted to make room for new downloads. The cache rebuilds its index from existing files on server restart.

### Cache Stats (available via admin API)

```json
{
  "disk_cache": {
    "cached_files": 12,
    "total_size_mb": 245.6,
    "max_size_mb": 1024,
    "usage_percent": 24.0,
    "hits": 156,
    "misses": 43,
    "hit_rate": 78.4
  }
}
```

---

## Database Management

### SQLite Overview

The application uses a **single SQLite file** (`student_library.db`) with the following tables:

| Table | Purpose |
|-------|---------|
| `users` | User accounts, roles, passwords |
| `resources` | File metadata, Telegram IDs, tags |
| `downloads` | Download history (who, what, when) |
| `ratings` | User reviews and star ratings |
| `reports` | Content reports from users |
| `audit_log` | Admin action history |
| `departments` | Academic departments |
| `courses` | Course catalog |

### Database Location

```
backend/
├── student_library.db          ← Primary database
├── student_library_backup.db   ← Backup copy
└── corrupt_backups/            ← Quarantined corrupt files
    ├── corrupt_20260301_143000_student_library.db
    └── ...
```

### Performance Settings

The database is configured with:
- **WAL mode** (Write-Ahead Logging) — allows concurrent reads and writes
- **Foreign keys ON** — data integrity enforcement
- **Async via aiosqlite** — non-blocking database operations

---

## Database Resilience

The application handles every possible database failure scenario automatically:

### Startup Resolution Flow

```
Server Starts
    │
    ├── DB file exists?
    │   ├── YES → Validate SQLite header + integrity check
    │   │         ├── VALID → ✅ Use it
    │   │         └── CORRUPT → Quarantine it
    │   │                       ├── Backup exists?
    │   │                       │   ├── YES + VALID → Restore from backup ✅
    │   │                       │   ├── YES + CORRUPT → Quarantine backup too
    │   │                       │   │                    → Create fresh DB ✅
    │   │                       │   └── NO → Create fresh DB ✅
    │   │                       └── Seed default admin user
    │   │
    │   └── NO → DB missing
    │             ├── Backup exists?
    │             │   ├── YES + VALID → Restore from backup ✅
    │             │   ├── YES + CORRUPT → Quarantine backup
    │             │   │                  → Create fresh DB ✅
    │             │   └── NO → Create fresh DB ✅
    │             └── Seed default admin user
    │
    └── Create tables if not exist (always safe)
```

### Validation Checks

1. **File size check** — SQLite header is 100 bytes minimum
2. **Magic header** — Must start with `SQLite format 3`
3. **PRAGMA quick_check** — SQLite integrity verification
4. **Expected tables** — At least 3 of 4 core tables must exist (users, resources, downloads, ratings)

### What Happens If...

| Scenario | What Happens |
|----------|-------------|
| DB file deleted while server running | Next query fails, admin must restart server |
| DB file deleted before server start | Auto-creates fresh DB, seeds admin user |
| DB file corrupted | Quarantined → backup restored → or fresh DB created |
| Backup file is corrupt | Backup quarantined, fresh DB created |
| Someone places a wrong file as DB | Validation fails (wrong header), quarantined |
| Server crashes mid-write | WAL mode ensures data consistency on restart |
| Someone places a valid backup DB | If primary is missing, backup is auto-restored |

---

## Backup & Recovery

### Creating a Backup

Backups can be created via the admin API:

```http
POST /api/v1/admin/database/backup
Authorization: Bearer <admin_token>
```

Response:
```json
{
  "status": "success",
  "message": "Backup created successfully",
  "path": "/backend/student_library_backup.db",
  "size": 221184,
  "timestamp": "2026-03-05T14:00:00Z"
}
```

### Manual Backup

Simply copy the database file:
```bash
cp backend/student_library.db backend/student_library_backup.db
```

### Restoring from Backup

**Automatic:** Place a valid `student_library_backup.db` file in the `backend/` directory. If the primary DB is missing or corrupt, the server will automatically restore from backup on startup.

**Manual:**
```bash
# Stop the server first
# Replace primary with backup
cp backend/student_library_backup.db backend/student_library.db
# Restart server
```

### Health Check

Monitor database health via the admin API:

```http
GET /api/v1/admin/database/health
```

Response:
```json
{
  "status": "healthy",
  "file_exists": true,
  "file_size": 221184,
  "backup_exists": true,
  "backup_size": 221184,
  "user_count": 5,
  "issues": []
}
```

---

## Environment Configuration

All Telegram and database settings are configured via the `.env` file in the `backend/` directory:

```env
# ──── Telegram Settings ────
TELEGRAM_API_ID=16501053
TELEGRAM_API_HASH=d8c9b01c863dabacc484c2c06cdd0f6e
TELEGRAM_BOT_TOKEN=8385481456:AAFk2g6SPQGmCN-1lXFZjspV8ZLhh1MpoF0
TELEGRAM_PRIMARY_CHANNEL=-1002284190309
TELEGRAM_BACKUP_CHANNEL=-1002284190309      # Can be same or different channel
TELEGRAM_OWNER_ID=5422016608                # Only this user can use bot commands

# ──── File Uploads ────
MAX_FILE_SIZE_MB=50                          # Max 50MB per file (Telegram limit: 2GB)
ALLOWED_EXTENSIONS=pdf,docx,pptx,xlsx,zip,txt,md,jpg,png

# ──── Security ────
SECRET_KEY=change-this-in-production
JWT_SECRET_KEY=change-this-jwt-secret

# ──── Application ────
APP_URL=http://127.0.0.1:3000               # Used in bot messages for resource links
ENVIRONMENT=development
DEBUG=true
```

### How to Get Telegram Credentials

1. **API ID & Hash:** Go to [my.telegram.org](https://my.telegram.org) → API Development Tools → Create Application
2. **Bot Token:** Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token
3. **Channel ID:** 
   - Create a private channel
   - Add your bot as admin
   - Forward any message from the channel to [@userinfobot](https://t.me/userinfobot) — it will show the channel ID (starts with `-100`)
4. **Owner ID:** Send a message to [@userinfobot](https://t.me/userinfobot) — it shows your user ID

---

## Edge Cases & Error Handling

### Telegram Errors

| Error | Cause | Handling |
|-------|-------|---------|
| `FloodWait` | Too many API requests | Auto-sleep for required seconds, then retry |
| `FileNotFoundInTelegram` | Message was deleted from channel | Returns HTTP 404 to user with clear message |
| `message.empty` | Pyrogram flags deleted messages | Treated as file-not-found (404) |
| Network timeout | Telegram API unreachable | Returns HTTP 500, user can retry |
| Bot not in channel | Bot lacks admin permissions | Upload fails with clear error message |

### Database Errors

| Error | Cause | Handling |
|-------|-------|---------|
| DB file missing | Manual deletion or disk issue | Auto-restore from backup or create fresh |
| DB file corrupt | Disk corruption, crash during write | Quarantine + backup restore or fresh create |
| Backup corrupt | Bad copy or manual corruption | Quarantine backup + create fresh DB |
| Wrong DB file | Replaced with non-SQLite file | Validation fails, quarantined |
| Tables missing | Partial corruption | `create_all()` recreates missing tables |

---

## Troubleshooting

### "Telegram client not connected"

**Cause:** Invalid credentials or network issue.

**Fix:**
1. Check `.env` has correct `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN`
2. Ensure the bot is not blocked or revoked
3. Check internet connectivity
4. Look at backend logs for specific error

### "File is no longer available on the storage server"

**Cause:** The file's message was deleted from the Telegram channel.

**Fix:**
1. The file cannot be recovered unless a backup exists
2. Re-upload the resource through the website
3. Prevent by not manually deleting messages in the storage channel

### "Database file is missing"

**Cause:** The `student_library.db` file was deleted.

**Fix:**
1. If `student_library_backup.db` exists, the server auto-restores on restart
2. If no backup, a fresh database is created with a default admin account
3. Email: `blasteranna1414@gmail.com` / Password: `Blaster1414&`

### "Upload failed: FloodWait"

**Cause:** Too many uploads in a short time.

**Fix:**
1. This is handled automatically — the bot sleeps for the required time
2. If persistent, space out uploads (wait ~30 seconds between uploads)
3. Consider using a separate bot for high-volume uploads

### Cache not clearing

**Clear the disk cache manually:**
```bash
# Delete all cached files
rm -rf backend/file_cache/*
```

Or via the admin API:
```http
POST /api/v1/admin/cache/clear
Authorization: Bearer <admin_token>
```
