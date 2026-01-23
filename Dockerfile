# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

# --- Stage 2: Final Runtime ---
FROM python:3.11-slim

# Install system dependencies (Node.js, Nginx, Supervisor)
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Setup Backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app/ ./backend/app/
COPY backend/alembic/ ./backend/alembic/
COPY backend/alembic.ini ./backend/
COPY backend/scripts/ ./backend/scripts/

# 2. Setup Frontend (Standalone)
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static

# 3. Setup Configs
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -rf /etc/nginx/sites-enabled/default

# 4. Environment
ENV PYTHONPATH=/app/backend
ENV PORT=80
EXPOSE 80

# 5. Start Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
