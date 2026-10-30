# 📚 Student Resource Library

> Enterprise-grade student resource sharing platform with unlimited cloud storage via Telegram, built with **Next.js 14** and **FastAPI**.

[![Python](https://img.shields.io/badge/python-3.11+-green.svg)]()
[![Next.js](https://img.shields.io/badge/next.js-14-black.svg)]()
[![FastAPI](https://img.shields.io/badge/fastapi-0.109-teal.svg)]()

---

## ✨ Features

### For Students
- **Upload & Share** — Share notes, assignments, exam papers, and study materials
- **Browse & Search** — Full-text search with filters by department, course, semester, and tags
- **Download & Preview** — Download files, or preview inline in the browser (PDF, DOCX, PPTX, XLSX, TXT, MD, JPG, PNG; ZIP shows a file listing) with a distraction-free fullscreen study mode
- **Rate & Review** — Rate resources with 1–5 stars and leave comments
- **Profile Dashboard** — Track uploads, downloads, and storage usage
- **Password Protection** — Optionally protect sensitive files with a password

### For Owners / Admins
- **Admin Dashboard** — Real-time stats: users, resources, downloads, storage usage
- **Department & Course Management** — Full CRUD for academic departments and courses
- **Resource Moderation** — Approve, reject, or flag uploaded resources
- **User Management** — View users, assign roles (student/moderator/admin), ban/unban
- **Report Handling** — Review and resolve user-submitted reports
- **Bulk Operations** — Bulk delete resources, clear all data (with confirmation)
- **System Health Monitoring** — Telegram API, in-memory cache, and SQLite status

### Security & Infrastructure
- **JWT Authentication** with access + refresh tokens (24h / 30 days)
- **MFA Support** — TOTP-based two-factor authentication (Google Authenticator)
- **Rate Limiting** — Configurable per-minute request limits
- **Telegram Storage** — Files stored in Telegram channels (unlimited, free)
- **SQLite Database** — Zero-config, portable, no external DB setup needed
- **In-Memory Caching** — No Redis required, lightweight built-in cache

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy (async), Pydantic v2 |
| **Database** | SQLite (via aiosqlite) |
| **File Storage** | Telegram Channels (via Pyrogram/Pyrofork) |
| **Auth** | JWT (python-jose), bcrypt, TOTP (pyotp) |
| **Monitoring** | Prometheus metrics, Sentry integration (optional) |
| **Deployment** | Docker (single container), Nginx reverse proxy |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **npm 9+**

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Students-main
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from config defaults or edit)
# See docs/OWNER_GUIDE.md for all environment variables

# Start the backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 4. Access the Application

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

---

## 📁 Project Structure

```
Students-main/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/             # API route handlers
│   │   │   ├── admin/          # Admin sub-routes (departments, courses, moderation, users)
│   │   │   ├── admin.py        # Admin dashboard, user mgmt, reports, resource mgmt
│   │   │   ├── auth.py         # Register, login, logout, MFA, token refresh
│   │   │   ├── resources.py    # Upload, download, preview, CRUD
│   │   │   ├── search.py       # Full-text search with filters
│   │   │   ├── ratings.py      # Star ratings and reviews
│   │   │   ├── reports.py      # User-submitted reports
│   │   │   └── deps.py         # Auth dependencies (get_current_user, get_admin_user)
│   │   ├── core/               # Config, database, security, middleware
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Telegram storage, cache, email services
│   │   └── main.py             # FastAPI app entry point
│   ├── requirements.txt
│   └── .env                    # Environment variables (create from template)
│
├── frontend/                   # Next.js 14 Frontend
│   ├── app/                    # Next.js App Router pages
│   │   ├── admin/              # Admin panel (dashboard, departments, courses, moderation, resources)
│   │   ├── auth/               # Login & Register pages
│   │   ├── browse/             # Browse & search resources
│   │   ├── resources/[slug]/   # Resource detail page
│   │   ├── upload/             # Upload resource form
│   │   ├── profile/            # User profile & stats
│   │   ├── settings/           # User account settings
│   │   └── page.tsx            # Homepage
│   ├── components/             # Reusable UI components
│   ├── lib/                    # API client, auth context, utilities
│   └── package.json
│
├── docs/                       # Governed documentation
│   ├── ARCHITECTURE.md         # Map: structure, ownership, "where is X" jump table
│   ├── STATUS.md               # Current health, open owner actions, delete-zone
│   ├── DECISIONS.md            # Append-only decision & history log
│   ├── backend.md              # Backend architecture & ops runbook
│   ├── API.md                  # API reference
│   ├── OWNER_GUIDE.md          # Admin/Owner comprehensive guide
│   ├── USER_GUIDE.md           # Student user guide
│   └── DEPLOYMENT.md           # Production deployment guide
│
├── audit/                      # Completed audit campaign reports (historical)
├── tasks/                      # Completed upgrade campaign ledgers (historical)
│
├── AGENTS.md                   # Project constitution (rules for agents/contributors)
├── PRODUCT.md                  # Product intent & principles
├── DESIGN.md                   # Design system tokens & rationale
├── CONTRIBUTING.md             # Contribution workflow
├── TELEGRAM_AND_DATABASE_GUIDE.md  # Storage & database internals
├── Dockerfile                  # Single-container Docker build
├── nginx.conf                  # Nginx reverse proxy config
└── README.md                   # This file
```

---

## 📚 Documentation

| Start here | File |
|---|---|
| **What is this project?** | `PRODUCT.md` + this README |
| **Contributing / agent rules** | `AGENTS.md` (constitution), `CONTRIBUTING.md` (workflow) |
| **Where does X live?** | `docs/ARCHITECTURE.md` |
| **Current status & blockers** | `docs/STATUS.md` |
| **Why was Y decided?** | `docs/DECISIONS.md`, `audit/`, `tasks/` |
| **Run / operate it** | below (Quick Start), `docs/DEPLOYMENT.md`, `docs/OWNER_GUIDE.md` |
| **Backend internals** | `docs/backend.md`, `TELEGRAM_AND_DATABASE_GUIDE.md` |
| **API** | `docs/API.md` + Swagger at `/docs` |
| **Using the site** | `docs/USER_GUIDE.md` |
| **Design system** | `DESIGN.md` |

---

## 🐳 Docker Deployment

Build and run everything in a single container:

```bash
# Build the image
docker build -t student-library .

# Run the container
docker run -p 80:80 \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32) \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e TELEGRAM_PRIMARY_CHANNEL=your_channel_id \
  student-library
```

Access at **http://localhost**.

---

## 🔐 Default Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Max file size | 50 MB | Per-upload limit |
| Storage quota | Unlimited (100 TB) | Per-user storage |
| Token expiry | 24 hours / 30 days | Access / Refresh |
| Rate limit | 60 req/min | Per IP address |
| Allowed formats | PDF, DOCX, PPTX, XLSX, ZIP, TXT, MD, JPG, PNG | Upload types |
| Auto-approval | Enabled | Resources go live immediately |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Owner Guide](docs/OWNER_GUIDE.md) | Complete admin/owner reference |
| [User Guide](docs/USER_GUIDE.md) | Student user guide |
| [API Reference](docs/API.md) | REST API endpoints |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |

---

## 🧪 Testing

### Backend API Tests

```bash
cd backend
python -m pytest tests/ -v --cov=app
```

### Frontend Type Check

```bash
cd frontend
npm run type-check
npm run lint
```

---

## 📄 License

No LICENSE file is currently present in the repository — the license is
**to be finalized by the owner** (this README previously claimed MIT without
the file; tracked in `docs/STATUS.md` owner actions).

---

<p align="center">
  Built with ❤️ for students, by students.
</p>
