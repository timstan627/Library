# syntax=docker/dockerfile:1

# --- Stage 1: Build Frontend ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
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
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Expose ONLY port 80 for Koyeb to route external traffic through Nginx
EXPOSE 80

# Entrypoint script
COPY <<EOF /app/start.sh
#!/bin/sh
# Start Backend
cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
# Start Frontend - Explicitly set PORT to 3000 to avoid clash with Nginx on 80
cd /app/frontend && PORT=3000 HOSTNAME=0.0.0.0 node server.js &
# Start Nginx
nginx -g "daemon off;"
EOF

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
