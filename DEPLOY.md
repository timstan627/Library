# Deployment Guide

This project is ready for deployment on VPS or PaaS platforms (like Koyeb, Render, Railway).

## Prerequisites

- **MongoDB Atlas**: You need a MongoDB connection string.
- **Redis**: Required for background tasks (Celery).
- **Telegram API**: App ID and Hash from my.telegram.org.

## Environment Variables

Configure these variables in your deployment environment:

### Backend
| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_NAME` | App Name | `Student Library` |
| `API_V1_STR` | API Prefix | `/api/v1` |
| `SECRET_KEY` | Security Key | Generate with `openssl rand -hex 32` |
| `ALGORITHM` | JWT Algo | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token Validity | `11520` (8 days) |
| `DATABASE_URL` | MongoDB URI | `mongodb+srv://user:pass@cluster.mongodb.net/dbname` |
| `REDIS_URL` | Redis URI | `redis://user:pass@host:port/0` |
| `TELEGRAM_API_ID` | Telegram App ID | `123456` |
| `TELEGRAM_API_HASH` | Telegram Hash | `abcdef123456...` |
| `TELEGRAM_BOT_TOKEN` | Bot Token | `123456:ABC-DEF...` |
| `TELEGRAM_CHANNEL_ID` | Channel ID | `-1001234567890` |
| `CORS_ORIGINS` | Frontend URL | `https://your-frontend-domain.com` |

### Frontend
| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend URL | `https://your-backend-domain.com` |

## Deployment Options

### Option 1: Docker (VPS / Koyeb)

The project includes production Dockerfiles.

**Backend:**
1.  Use `backend/Dockerfile.prod`.
2.  Expose port `8000`.
3.  Command: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000`

**Frontend:**
1.  Use `frontend/Dockerfile.prod` (ensure `NEXT_PUBLIC_API_URL` is set at build time or runtime depending on setup, Next.js static generation requires it at build time usually, but client-side fetch uses runtime if configured).
2.  Expose port `3000`.

### Option 2: Manual (VPS)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --daemon
# Start Celery
celery -A app.core.celery_app worker --loglevel=info --detach
```

**Frontend:**
```bash
cd frontend
npm install
npm run build
npm start
```
