# API Testing Guide

## Quick Test (Manual)

### 1. Start the Server
```bash
python start_server.py
```

Or with uvicorn directly:
```bash
uvicorn api.main:app --reload
```

Server starts at: `http://localhost:8000`

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T..."
}
```

### 3. View API Documentation
Open in browser: `http://localhost:8000/docs`

### 4. Test with Sample Request

**PowerShell:**
```powershell
$body = @{
    role = "Senior Software Engineer"
    jd_text = "We need a Python developer with FastAPI experience and cloud platform knowledge."
    bullets = @(
        "Built REST APIs using Python",
        "Deployed applications to AWS"
    )
    settings = @{
        max_len = 30
        variants = 2
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/test/process-sync" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/test/process-sync \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## Expected Response

```json
{
  "job_id": "01HX5PQRS...",
  "summary": {
    "role": "Senior Software Engineer",
    "top_terms": ["Python", "FastAPI", "AWS", "cloud", "REST API"],
    "coverage": {
      "hit": ["Python", "FastAPI"],
      "miss": ["microservices", "Docker"]
    }
  },
  "results": [
    {
      "original": "Built REST APIs using Python",
      "revised": [
        "Architected Python REST APIs using FastAPI, serving 1M+ requests daily",
        "Developed scalable backend APIs with Python and FastAPI framework"
      ],
      "scores": {
        "relevance": 95,
        "impact": 88,
        "clarity": 92
      },
      "notes": "Added JD-aligned terms (FastAPI), emphasized scalability"
    }
  ],
  "red_flags": []
}
```

## Environment Setup

Make sure you have API keys set:

```bash
# .env file
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
```

## Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000  # Windows
lsof -i :8000  # Mac/Linux

# Try different port
uvicorn api.main:app --port 8001
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### API key not working
```bash
# Check .env file exists
ls .env

# Verify format (no quotes)
OPENAI_API_KEY=sk-proj-...
```

## Next.js Integration Test

Once the API is running locally, test from your Next.js app:

```typescript
// pages/api/test-resume-api.ts
export default async function handler(req, res) {
  const response = await fetch('http://localhost:8000/health');
  const data = await response.json();
  res.status(200).json(data);
}
```

Visit: `http://localhost:3000/api/test-resume-api`

## Production Testing

After deploying to Railway/Render/etc:

```bash
# Replace with your production URL
curl https://your-app.railway.app/health
```

Test full request:
```bash
curl -X POST https://your-app.railway.app/api/test/process-sync \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

