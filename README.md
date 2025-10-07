# ATS Resume Bullet Revisor API

> Production-ready FastAPI service for rewriting resume bullets to be ATS-friendly and JD-aligned

## Quick Deploy to Production

### Railway (Recommended - 1 Click)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Render.com
1. Connect your GitHub repo
2. Select "Web Service"
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### Google Cloud Run
```bash
gcloud run deploy ats-resume-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Environment Variables (Required)

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Config
LLM_PROVIDER=openai  # or anthropic
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.3
```

## API Endpoints

### POST `/api/resume/process`
Revise resume bullets with job description alignment.

**Request:**
```json
{
  "role": "Senior Software Engineer",
  "jd_text": "We are looking for...",
  "bullets": [
    "Built scalable systems",
    "Led team of engineers"
  ],
  "settings": {
    "max_len": 30,
    "variants": 2
  }
}
```

**Response:**
```json
{
  "job_id": "01HX5PQRS...",
  "summary": {
    "role": "Senior Software Engineer",
    "top_terms": ["Python", "FastAPI", "AWS", ...]
  },
  "results": [
    {
      "original": "Built scalable systems",
      "revised": [
        "Architected Python microservices on AWS, scaling to 1M+ daily users",
        "Developed cloud-native applications using FastAPI and serverless architecture"
      ],
      "scores": {
        "relevance": 92,
        "impact": 88,
        "clarity": 95
      }
    }
  ]
}
```

### GET `/health`
Health check endpoint.

## Local Development

```bash
# 1. Clone repo
git clone <your-repo>
cd ATS_Resume_Agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp env.example .env
# Edit .env with your API keys

# 4. Run server
uvicorn api.main:app --reload
```

Server runs at: `http://localhost:8000`

## Next.js Integration

```typescript
// lib/api.ts
export async function reviseResumeBullets(
  bullets: string[],
  role: string,
  jdText: string
) {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/resume/process`,
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
  
  return response.json();
}
```

## Architecture

```
┌─────────────────┐
│   Next.js App   │
│   (Frontend)    │
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│   FastAPI       │
│   (This Repo)   │
└────────┬────────┘
         │
         ├─▶ OpenAI/Anthropic (LLM)
         ├─▶ JD Parser Agent
         ├─▶ Rewriter Agent
         ├─▶ Scorer Agent
         └─▶ Validator Agent
```

## Project Structure

```
├── agents/          # AI agents (parsing, rewriting, scoring, validation)
├── api/             # FastAPI endpoints
├── orchestrator/    # State machine workflow
├── ops/             # Utilities (logging, LLM client, retry logic)
├── schemas/         # Pydantic models
├── Dockerfile       # Container build
├── requirements.txt # Python dependencies
└── pyproject.toml   # Project config
```

## Production Checklist

- [ ] Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable
- [ ] Set `LLM_PROVIDER` to `openai` or `anthropic`
- [ ] Configure CORS origins in `api/main.py` for your frontend domain
- [ ] Set up monitoring/alerting (Sentry, DataDog, etc.)
- [ ] Enable rate limiting if needed
- [ ] Set up SSL/TLS certificate

## Monitoring

Health check: `GET /health`

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T10:30:00Z"
}
```

## License

MIT

## Support

- Issues: GitHub Issues
- API Docs: `/docs` (FastAPI auto-generated)
