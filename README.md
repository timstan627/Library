# Ultimate Student Resource Library

Enterprise-grade student resource library with **Telegram-based unlimited cloud storage**.

## 🚀 Features

- **Unlimited Storage** - Files stored in Telegram channels with backup redundancy
- **Advanced Search** - Full-text search with PostgreSQL tsvector
- **Role-based Access** - Students, moderators, and admin roles
- **2FA Support** - TOTP-based multi-factor authentication
- **Dark Theme UI** - MediaPeek-inspired modern dark interface
- **Real-time Analytics** - Download tracking and resource popularity

## 📋 Tech Stack

### Backend
- **FastAPI** - High-performance async Python framework
- **PostgreSQL 15** - Primary database with full-text search
- **Redis 7** - Caching and Celery broker
- **SQLAlchemy 2.0** - Async ORM with connection pooling
- **Pyrogram** - Telegram API integration
- **Celery** - Background task processing

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Data fetching and caching
- **Framer Motion** - Animations

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & Configure

```bash
git clone <repository-url>
cd Students

# Copy environment template
cp .env.example .env

# Configure your Telegram credentials in .env
# Required: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_PRIMARY_CHANNEL
```

### 2. Start with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── tasks/           # Celery background tasks
│   ├── alembic/             # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   └── lib/                 # Utilities
├── docker-compose.yml
└── .env.example
```

## 🔐 Environment Variables

See `.env.example` for all available options:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `TELEGRAM_API_ID` | Telegram API ID |
| `TELEGRAM_API_HASH` | Telegram API Hash |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_PRIMARY_CHANNEL` | Channel ID for file storage |
| `JWT_SECRET_KEY` | Secret for JWT tokens |

## 🗄️ Database Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## 🧪 Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📦 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | User registration |
| `POST /api/v1/auth/login` | JWT authentication |
| `GET /api/v1/resources` | List resources |
| `POST /api/v1/resources/upload` | Upload file |
| `GET /api/v1/search` | Full-text search |
| `GET /api/v1/admin/dashboard` | Admin statistics |

## 🎨 UI Pages

| Page | Path | Description |
|------|------|-------------|
| Home | `/` | Landing page with features |
| Browse | `/browse` | Search and filter resources |
| Upload | `/upload` | Drag-and-drop upload |
| Resource | `/resources/[slug]` | Resource detail with ratings |
| Profile | `/profile` | User profile and uploads |
| Settings | `/settings` | Account settings and MFA |
| Admin | `/admin` | Dashboard and moderation |

## 📄 License

MIT License - see LICENSE file for details.
