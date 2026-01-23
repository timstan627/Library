# Deployment Guide

This project is configured for **single-container deployment** - everything runs in one Docker container.

## What's Included

The Docker container bundles:
- ✅ **Backend** (FastAPI on port 8000)
- ✅ **Frontend** (Next.js on port 3000)
- ✅ **Nginx** (Reverse proxy on port 80)
- ✅ **Supervisor** (Process management)

## Prerequisites

Before deploying, you need:

1. **MongoDB Database**
   - Sign up at [MongoDB Atlas](https://www.mongodb.com/atlas) (free tier available)
   - Create a cluster and get your connection string

2. **Telegram API Credentials**
   - Go to [my.telegram.org](https://my.telegram.org)
   - Create an application to get API ID and Hash
   - Create a bot via [@BotFather](https://t.me/BotFather) for the token
   - Create a private channel and get its ID (starts with -100)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | MongoDB connection string |
| `SECRET_KEY` | ✅ | Random string (32+ characters) |
| `TELEGRAM_API_ID` | ✅ | From my.telegram.org |
| `TELEGRAM_API_HASH` | ✅ | From my.telegram.org |
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `TELEGRAM_PRIMARY_CHANNEL` | ✅ | Channel ID for file storage |
| `NEXT_PUBLIC_API_URL` | ❌ | Leave empty for same-origin |

## Deploy to Koyeb

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### Step 2: Create Koyeb Service

1. Log in to [Koyeb](https://app.koyeb.com)
2. Click **Create Service**
3. Select **GitHub** as source
4. Choose your repository

### Step 3: Configure Build

| Setting | Value |
|---------|-------|
| **Builder** | Dockerfile |
| **Dockerfile path** | `Dockerfile` (default) |
| **Port** | `80` |

### Step 4: Add Environment Variables

Go to **Environment Variables** section and add all required variables from the table above.

### Step 5: Deploy

Click **Deploy** and wait for the build to complete (3-5 minutes).

Your app will be available at: `https://your-app-name.koyeb.app`

## Deploy to Other Platforms

### Railway

1. Connect GitHub repository
2. Add environment variables
3. Set port to `80`
4. Deploy

### Render

1. Create new Web Service
2. Connect repository
3. Set Docker as environment
4. Add environment variables
5. Deploy

### VPS (Manual)

```bash
# Clone repository
git clone <your-repo-url>
cd Students

# Build image
docker build -t student-library .

# Run container
docker run -d \
  -p 80:80 \
  -e DATABASE_URL="mongodb+srv://..." \
  -e SECRET_KEY="your-secret-key" \
  -e TELEGRAM_API_ID="123456" \
  -e TELEGRAM_API_HASH="abc123..." \
  -e TELEGRAM_BOT_TOKEN="123:ABC..." \
  -e TELEGRAM_PRIMARY_CHANNEL="-100..." \
  student-library
```

## Troubleshooting

### Build Fails
- Check Docker logs: `docker logs <container-id>`
- Ensure Dockerfile is in repository root

### Database Connection Error
- Verify DATABASE_URL is correct
- Check MongoDB Atlas IP whitelist (add 0.0.0.0/0 for cloud deployments)

### Telegram Not Working
- Verify all Telegram credentials are correct
- Make sure bot is added to the channel as admin
- Channel ID must include the -100 prefix

### 502 Bad Gateway
- Backend might be starting slowly, wait 30 seconds
- Check application logs for errors

## Health Check

Once deployed, verify these endpoints:

| Endpoint | Expected Response |
|----------|-------------------|
| `/` | Homepage loads |
| `/api/v1/stats` | JSON with resource counts |
| `/health` | `{"status": "healthy"}` |
