# Deploy to Render - Step by Step Guide

## ✅ Prerequisites (Already Done!)
- [x] Code pushed to GitHub: https://github.com/ChandlerShores/ATS_Resume_Agent
- [x] API tested and working locally
- [x] Dockerfile and requirements.txt ready

---

## Step 1: Create Render Account

1. Go to **https://render.com**
2. Click **"Get Started"**
3. Sign up with GitHub (easiest - auto-connects your repos)

---

## Step 2: Create New Web Service

1. Click **"New +"** (top right)
2. Select **"Web Service"**

You'll see a list of your GitHub repositories.

---

## Step 3: Connect Your Repository

1. Find **"ChandlerShores/ATS_Resume_Agent"** in the list
2. Click **"Connect"**

If you don't see it:
- Click **"Configure account"**
- Give Render access to your repos
- Refresh and find your repo

---

## Step 4: Configure Service

### Basic Settings:
```
Name: ats-resume-agent
Region: Oregon (US West) or closest to you
Branch: main
Runtime: Python 3
```

### Build & Deploy:
```
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

**⚠️ Important:** Use `$PORT` (Render provides this automatically)

### Plan:
```
Instance Type: Free
```

---

## Step 5: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these **one by one**:

1. **OPENAI_API_KEY**
   ```
   Value: sk-proj-... (your actual API key)
   ```

2. **LLM_PROVIDER**
   ```
   Value: openai
   ```

3. **LLM_MODEL**
   ```
   Value: gpt-4-turbo-preview
   ```

4. **LLM_TEMPERATURE**
   ```
   Value: 0.3
   ```

---

## Step 6: Deploy!

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Install dependencies (~2-3 minutes)
   - Start your API
   - Give you a URL

**Your URL will be:**
```
https://ats-resume-agent-<random>.onrender.com
```

---

## Step 7: Wait for Deployment (~3-5 minutes)

You'll see a build log. Wait for:
```
==> Build successful 🎉
==> Deploying...
==> Your service is live 🎉
```

---

## Step 8: Test Your API

### Test Health Endpoint:
```bash
curl https://ats-resume-agent-<your-id>.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T..."
}
```

### View API Docs:
Open in browser:
```
https://ats-resume-agent-<your-id>.onrender.com/docs
```

### Test Full Request:
```bash
curl -X POST https://ats-resume-agent-<your-id>.onrender.com/api/test/process-sync \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "jd_text": "Looking for Python developer",
    "bullets": ["Built APIs with Python"],
    "settings": {"max_len": 30, "variants": 2}
  }'
```

---

## Step 9: Configure for Next.js

In your Next.js project, add to `.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://ats-resume-agent-<your-id>.onrender.com
```

Then in your Next.js code:
```typescript
const response = await fetch(
  `${process.env.NEXT_PUBLIC_API_URL}/api/test/process-sync`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      role: "Software Engineer",
      jd_text: jobDescription,
      bullets: resumeBullets,
      settings: { max_len: 30, variants: 2 }
    })
  }
);

const data = await response.json();
// data.results[0].revised = ["variant 1", "variant 2"]
```

---

## ⚠️ Free Tier Limitations

### What You Get:
- ✅ 750 hours/month (25 days)
- ✅ Automatic HTTPS
- ✅ Custom domains
- ✅ Auto-deploys from GitHub

### Limitations:
- ⚠️ **Sleeps after 15 minutes** of inactivity
- ⚠️ **30-second cold start** when it wakes up
- ⚠️ 512 MB RAM
- ⚠️ Shared CPU

### When to Upgrade ($7/month):
- No cold starts
- Always-on
- 512 MB RAM → 2 GB RAM
- Faster CPU

---

## Troubleshooting

### "Build failed"
- Check the build log
- Usually: Missing dependency in requirements.txt
- Fix: Update requirements.txt and push to GitHub (auto-redeploys)

### "Service unreachable"
- Free tier might be sleeping
- Wait 30 seconds and retry
- Or upgrade to paid tier ($7/month)

### "API key error"
- Check environment variables in Render dashboard
- Make sure OPENAI_API_KEY is set correctly
- Redeploy after adding env vars

### "CORS error" from Next.js
- Update `api/main.py` to allow your Next.js domain:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],  # Add your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Auto-Deploy Setup (Already Configured!)

Render automatically redeploys when you push to GitHub:

```bash
# Make a change
git add .
git commit -m "Update API"
git push origin main

# Render automatically:
# 1. Detects push
# 2. Rebuilds
# 3. Redeploys
# (~2-3 minutes)
```

---

## Monitoring

### View Logs:
1. Go to Render dashboard
2. Click your service
3. Click **"Logs"** tab
4. See real-time logs

### View Metrics:
1. Click **"Metrics"** tab
2. See:
   - CPU usage
   - Memory usage
   - Request count
   - Response times

---

## Cost Estimates

### Free Tier:
```
$0/month
- Perfect for testing
- Good for low-traffic apps
- Sleeps after 15 min
```

### Starter Tier ($7/month):
```
$7/month flat fee
- No cold starts
- 512 MB RAM
- Perfect for production with light traffic
```

### Pro Tier ($25/month):
```
$25/month
- 2 GB RAM
- Auto-scaling
- Priority support
```

---

## Next Steps After Deployment

1. ✅ **Test your API** (health + full request)
2. ✅ **Add to Next.js** (.env.local)
3. ✅ **Test integration** (frontend → API)
4. ✅ **Monitor for a few days** (check logs)
5. ✅ **Upgrade if needed** (if cold starts are annoying)

---

## You're All Set! 🚀

Your API will be live at:
```
https://ats-resume-agent-<your-id>.onrender.com
```

Takes ~3-5 minutes for first deployment.

**Need help? The Render dashboard shows real-time build logs!**

