# syntax=docker/dockerfile:1

# --- Stage 1: Build Frontend ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# --- Stage 2: Final Image ---
FROM python:3.11-slim
WORKDIR /app

# Install Node.js and Nginx
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static

# Copy Nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# Expose ports (Mainly 80 for Koyeb)
EXPOSE 80
EXPOSE 8000
EXPOSE 3000

# Entrypoint script
COPY <<EOF /app/start.sh
#!/bin/sh
# Start Backend
cd /app/backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 &
# Start Frontend
cd /app/frontend && HOSTNAME=127.0.0.1 node server.js &
# Start Nginx
nginx -g "daemon off;"
EOF

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
