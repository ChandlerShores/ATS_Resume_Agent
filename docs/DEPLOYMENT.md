# Deployment Guide

## Overview

This guide covers deploying the ATS Resume Agent API to production. The application is designed to be deployed as a containerized service or Python web application.

## Prerequisites

- GitHub account (for auto-deployment)
- OpenAI or Anthropic API key
- Chosen deployment platform account

## Deployment Platforms

### Option 1: Render.com (Recommended)

**Pre-configured via `render.yaml`**

#### Setup Steps:

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub (easiest)

3. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your repository
   - Render auto-detects `render.yaml` configuration

4. **Add Environment Variables**
   
   Required:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```
   
   Optional:
   ```
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   LLM_TEMPERATURE=0.3
   MAX_DAILY_COST=100.0
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait 3-5 minutes for build
   - Your API will be live at: `https://ats-resume-agent-xxx.onrender.com`

#### Free Tier Limitations:
- ⚠️ Sleeps after 15 minutes of inactivity
- ⚠️ 30-second cold start when waking
- ✅ 750 hours/month free
- ✅ Automatic HTTPS
- ✅ Auto-deploy from GitHub

#### Upgrade ($7/month):
- No cold starts
- Always-on
- 512 MB → 2 GB RAM
- Faster CPU

---

### Option 2: Railway (Alternative)

```bash
# Install Railway CLI
npm install -g railway

# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# Add environment variable
railway variables set OPENAI_API_KEY=sk-...
```

**Features:**
- Auto-detects Dockerfile
- Free tier available
- One-click deploy

---

### Option 3: Google Cloud Run

```bash
# Deploy (requires gcloud CLI)
gcloud run deploy ats-resume-api \
  --source . \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=sk-... \
  --allow-unauthenticated
```

**Features:**
- Serverless containers
- Pay per use
- Auto-scaling
- Global edge deployment

---

### Option 4: Docker (Any Platform)

#### Build Image:
```bash
docker build -t ats-resume-agent .
```

#### Run Locally:
```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e LLM_PROVIDER=openai \
  -e LLM_MODEL=gpt-4o-mini \
  ats-resume-agent
```

#### Deploy to Cloud:
- AWS ECS
- Azure Container Instances
- DigitalOcean App Platform
- Kubernetes cluster

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative) | `sk-ant-...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4-turbo-preview` | Model name |
| `LLM_TEMPERATURE` | `0.3` | Temperature (0.0-1.0) |
| `LLM_MAX_TOKENS` | `2000` | Max tokens per call |
| `MAX_DAILY_COST` | `100.0` | Max daily LLM cost ($) |
| `MAX_REQUESTS_PER_DAY` | `1000` | Max requests per day |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `10` | Rate limit per IP |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Post-Deployment Testing

### 1. Health Check
```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-11T...",
  "active_jobs": 0
}
```

### 2. API Documentation
Visit in browser:
```
https://your-app.onrender.com/docs
```

### 3. Full Request Test
```bash
curl -X POST https://your-app.onrender.com/api/test/process-sync \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "jd_text": "Looking for Python developer with FastAPI experience",
    "bullets": ["Built REST APIs with Python"],
    "settings": {"max_len": 30, "variants": 2}
  }'
```

---

## Frontend Integration (Next.js)

### 1. Add API URL to Environment
`.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-app.onrender.com
```

### 2. Call API from Next.js
```typescript
// app/api/revise-bullets/route.ts
export async function POST(req: Request) {
  const { bullets, role, jdText } = await req.json();
  
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/test/process-sync`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        jd_text: jdText,
        bullets,
        settings: { max_len: 30, variants: 2 }
      })
    }
  );
  
  return Response.json(await response.json());
}
```

### 3. Update CORS (if needed)
In `api/main.py`, update allowed origins:
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "https://your-app.vercel.app"  # Add your production domain
    ]
```

---

## Monitoring & Maintenance

### View Logs (Render)
1. Go to Render dashboard
2. Click your service
3. Click "Logs" tab
4. See real-time structured JSON logs

### View Metrics (Render)
1. Click "Metrics" tab
2. Monitor:
   - CPU usage
   - Memory usage
   - Request count
   - Response times

### Cost Monitoring
Check health endpoint for cost warnings:
```bash
curl https://your-app.onrender.com/health
```

Response includes:
```json
{
  "cost_warnings": ["Cost limit: 82.3% used ($82.30/$100)"],
  "security": {
    "suspicious_ips": 0,
    "total_failed_attempts": 2
  }
}
```

---

## Troubleshooting

### Build Failed
**Symptom**: Deployment fails during build
**Solution**: 
- Check build logs in dashboard
- Verify `requirements.txt` has all dependencies
- Ensure Python 3.11+ is specified

### Service Unreachable
**Symptom**: 503 or timeout errors
**Solution**:
- Free tier may be sleeping (wait 30s)
- Check logs for startup errors
- Verify environment variables are set

### API Key Error
**Symptom**: 500 errors mentioning API key
**Solution**:
- Verify `OPENAI_API_KEY` in environment variables
- Check key has sufficient credits
- Redeploy after adding env vars

### CORS Error from Frontend
**Symptom**: Browser blocks requests
**Solution**:
- Add your frontend domain to `ALLOWED_ORIGINS`
- Redeploy
- Clear browser cache

### Rate Limit Exceeded
**Symptom**: 429 errors
**Solution**:
- Increase `MAX_REQUESTS_PER_DAY` limit
- Wait for daily reset (midnight UTC)
- Check `/health` for current usage

---

## Auto-Deployment

Render automatically redeploys on GitHub push:

```bash
# Make changes
git add .
git commit -m "Update API"
git push origin main

# Render automatically:
# 1. Detects push
# 2. Rebuilds (~2-3 minutes)
# 3. Redeploys
```

---

## Cost Estimates

### Free Tier (Render)
- $0/month
- Good for testing & low traffic
- Sleeps after 15 min inactivity

### Starter ($7/month)
- No cold starts
- 512 MB RAM
- Good for production with light traffic

### OpenAI API Costs (separate)
- GPT-4o-mini: ~$0.01 per request
- GPT-4-turbo: ~$0.05 per request
- App has built-in cost controls (default $100/day limit)

---

## Production Checklist

- [ ] Environment variables configured
- [ ] Health endpoint accessible
- [ ] API docs viewable at `/docs`
- [ ] Test request successful
- [ ] CORS configured for frontend domain
- [ ] Monitoring/alerting set up
- [ ] Cost limits appropriate
- [ ] Auto-deployment working

---

## Support

- **Render Issues**: https://render.com/docs
- **API Issues**: Check `/health` endpoint
- **Application Logs**: View in platform dashboard
- **Security Issues**: Enable security monitoring in `/health`

