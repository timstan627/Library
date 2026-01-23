# Deployment Guide

This project is fully configured for deployment on **Koyeb**.

## Prerequisites

1.  **GitHub Repository**: Push this project to a GitHub repository.
2.  **MongoDB Atlas**: Create a cluster and get your connection string (`mongodb+srv://...`).
3.  **Redis**: Get a Redis connection string (e.g., from Upstash or Koyeb Redis).
4.  **Telegram API**: Get your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

---

## Step 1: Deploy Backend (Koyeb)

1.  Log in to [Koyeb](https://app.koyeb.com).
2.  Click **Create App** (or select existing).
3.  Click **Create Service**.
4.  Select **GitHub** as the source.
5.  Select your repository.
6.  **Builder Configuration**:
    *   **Builder**: Dockerfile
    *   **Dockerfile Location**: `backend/Dockerfile.prod` (Important: include the folder path)
    *   **Privileged**: Unchecked
7.  **Service Name**: e.g., `student-lib-backend`
8.  **Ports**: Change to `8000` (HTTP)
9.  **Environment Variables**: Add the following:

| Variable | Value (Example) |
|----------|-----------------|
| `PROJECT_NAME` | `Student Library` |
| `API_V1_STR` | `/api/v1` |
| `SECRET_KEY` | *(Generate a random string)* |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` |
| `DATABASE_URL` | `mongodb+srv://user:pass@...` |
| `REDIS_URL` | `redis://default:pass@...` |
| `TELEGRAM_API_ID` | `123456` |
| `TELEGRAM_API_HASH` | `abcdef123...` |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` |
| `TELEGRAM_CHANNEL_ID` | `-100123...` |
| `CORS_ORIGINS` | `https://student-lib-frontend.koyeb.app` (You can add `*` first, then update later) |

10. Click **Deploy**.
11. **Copy the Public URL** of your new backend service (e.g., `https://student-lib-backend-org.koyeb.app`).

---

## Step 2: Deploy Frontend (Koyeb)

1.  In the same Koyeb App, click **Create Service**.
2.  Select **GitHub** and your repository again.
3.  **Builder Configuration**:
    *   **Builder**: Dockerfile
    *   **Dockerfile Location**: `frontend/Dockerfile.prod`
4.  **Service Name**: e.g., `student-lib-frontend`
5.  **Ports**: Change to `3000` (HTTP)
6.  **Environment Variables**:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://student-lib-backend-org.koyeb.app` (Your Backend URL from Step 1) |

7.  Click **Deploy**.

---

## Step 3: Final Configuration

1.  Go back to your **Backend Service** settings on Koyeb.
2.  Update `CORS_ORIGINS` to match your **Frontend Public URL** (e.g., `https://student-lib-frontend-org.koyeb.app`).
3.  Redeploy the Backend for changes to take effect.
