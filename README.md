# Student Resource Library

A modern, production-ready student resource sharing platform with **Telegram-based unlimited cloud storage**.

## Features

- **Unlimited File Storage** - Files stored in Telegram channels (no storage limits)
- **Full-Text Search** - Search by title, description, course code, and tags
- **Role-Based Access** - Students, Moderators, and Admins
- **Two-Factor Authentication** - TOTP-based MFA support
- **Modern Dark UI** - Beautiful, responsive interface
- **File Preview** - View PDFs and images before downloading
- **Ratings & Reviews** - Community-driven quality feedback

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async Python API |
| **MongoDB** | Document database (via Beanie ODM) |
| **Pyrogram** | Telegram MTProto API for file storage |
| **JWT** | Secure authentication tokens |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Next.js 14** | React framework with App Router |
| **TypeScript** | Type-safe development |
| **Tailwind CSS** | Utility-first styling |
| **Axios** | API client |

### Infrastructure
| Component | Purpose |
|-----------|---------|
| **Nginx** | Reverse proxy and load balancing |
| **Supervisor** | Process management |
| **Docker** | Containerization |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # MongoDB document models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (Telegram, cache)
│   │   └── tasks/           # Background task functions
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Reusable React components
│   └── lib/                 # API client, auth context
├── Dockerfile               # Unified container build
├── nginx.conf               # Routing configuration
├── supervisord.conf         # Process management
└── DEPLOY.md                # Deployment instructions
```

## Local Development

### Prerequisites
- Node.js 20+
- Python 3.11+
- MongoDB (local or Atlas)
- Telegram API credentials

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install

# Run development server
npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | MongoDB connection string |
| `SECRET_KEY` | Random string for JWT signing |
| `TELEGRAM_API_ID` | Telegram API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Telegram API Hash |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_PRIMARY_CHANNEL` | Channel ID for file storage |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `true` | Enable debug mode |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT token lifetime |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload size |
| `ENABLE_MFA` | `true` | Enable 2FA support |

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Get JWT tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Revoke session

### Resources
- `GET /api/v1/resources` - List all resources
- `GET /api/v1/resources/{slug}` - Get resource details
- `POST /api/v1/resources/upload` - Upload new file
- `GET /api/v1/resources/{id}/download` - Download file
- `GET /api/v1/search` - Full-text search

### User
- `GET /api/v1/users/me` - Current user profile
- `PUT /api/v1/users/me` - Update profile
- `GET /api/v1/users/me/resources` - User's uploads

### Admin
- `GET /api/v1/admin/dashboard` - Platform statistics
- `GET /api/v1/admin/users` - User management
- `GET /api/v1/admin/moderation` - Content moderation queue

## UI Pages

| Page | Path | Access |
|------|------|--------|
| Home | `/` | Public |
| Browse | `/browse` | Public |
| Resource Detail | `/resources/[slug]` | Public |
| Upload | `/upload` | Authenticated |
| Profile | `/profile` | Authenticated |
| Settings | `/settings` | Authenticated |
| Admin Dashboard | `/admin` | Admin only |

## Deployment

See **[DEPLOY.md](./DEPLOY.md)** for complete deployment instructions.

**Quick Summary**: This project uses a single Docker container that runs the frontend, backend, and nginx together. Deploy to Koyeb or any Docker-compatible platform.

## License

MIT License - see LICENSE file for details.
