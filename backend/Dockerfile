FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (runtime deps only; dev/test deps live in
# requirements-dev.txt and must never ship in the image)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (respects .dockerignore — no .env, no live DB)
COPY . .

# Non-root runtime user; /app holds the SQLite DB + Pyrogram session files,
# so it must be writable by the app process.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Container-level liveness: /health exercises the DB (503 when degraded)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Run with uvicorn (single worker by design — in-memory rate limiting/cache
# and the SQLite file assume one process; see docs/backend.md)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
