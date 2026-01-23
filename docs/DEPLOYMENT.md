# Deployment Guide

This guide covers deploying the Student Resource Library to production.

## Prerequisites

- Linux server (Ubuntu 22.04 recommended)
- Docker & Docker Compose
- Domain name with DNS configured
- SSL certificate (Let's Encrypt recommended)

## Server Setup

### 1. Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin
```

### 2. Clone Repository

```bash
cd /opt
sudo git clone <repository-url> student-library
sudo chown -R $USER:$USER student-library
cd student-library
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required variables:**

```env
# Security (generate with: openssl rand -hex 32)
SECRET_KEY=<random-string>
JWT_SECRET_KEY=<random-string>
HMAC_SECRET_KEY=<random-string>
DB_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>

# Telegram
TELEGRAM_API_ID=<your-api-id>
TELEGRAM_API_HASH=<your-api-hash>
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_PRIMARY_CHANNEL=<channel-id>
TELEGRAM_BACKUP_CHANNEL=<backup-channel-id>

# Domain
DOMAIN=yourdomain.com
```

### 4. SSL Certificate

Using Let's Encrypt with Certbot:

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy to nginx directory
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

### 5. Deploy

```bash
# Build and start
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker exec -it students-backend alembic upgrade head

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

## Monitoring

### Health Check

```bash
curl https://yourdomain.com/health
```

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
```

### Metrics

Prometheus metrics available at `/metrics` (internal only).

## Backup

### Database

```bash
# Backup
docker exec students-db pg_dump -U admin student_library > backup.sql

# Restore
cat backup.sql | docker exec -i students-db psql -U admin student_library
```

### Files

Files are stored in Telegram channels and don't require local backup.

## Updating

```bash
cd /opt/student-library

# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build

# Run any new migrations
docker exec -it students-backend alembic upgrade head
```

## Troubleshooting

### Database Connection Failed

```bash
# Check database is running
docker compose -f docker-compose.prod.yml ps db

# Check logs
docker compose -f docker-compose.prod.yml logs db
```

### 502 Bad Gateway

```bash
# Check backend health
docker compose -f docker-compose.prod.yml ps backend
docker compose -f docker-compose.prod.yml logs backend
```

### SSL Certificate Expired

```bash
# Renew certificate
sudo certbot renew
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
docker compose -f docker-compose.prod.yml restart nginx
```
