# ATS Resume Rewriter API

FastAPI service that rewrites resume bullets to align with a Job Description (JD) and ATS best practices using GPT models.

## Requirements
- Python 3.11+
- OpenAI API key

## Setup
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copy .env.example to .env and add your OpenAI API key
cp .env.example .env
# Then edit .env and set: OPENAI_API_KEY=sk-your-key-here

# OR set environment variable directly:
# Windows PowerShell: $env:OPENAI_API_KEY = "sk-..."
# Linux/Mac: export OPENAI_API_KEY="sk-..."
```

## Run
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints
- GET `/health` → uptime, model, versions
- GET `/version` → versions
- POST `/api/rewrite` → rewrite bullets

### Request Body
```json
{
  "job_description": "string",
  "resume_bullets": ["string"],
  "params": {
    "target_tense": "present|past|auto",
    "max_words_per_bullet": 26,
    "seniority_hint": "IC mid|Manager|Director",
    "request_id": "uuid",
    "prompt_version": "1.0.0",
    "api_version": "1.0.0"
  }
}
```

### Notes
- JSON schema enforced via OpenAI `response_format=json_schema` and server-side validation.
- One repair retry is attempted on schema invalid.
- Structured JSON logs to stdout: `request_id`, `latency_ms`, `output_valid_json`, `grade_score`, `retry_attempts`, etc.

## Deploy on Render.com
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment: set `OPENAI_API_KEY`, optional `REDIS_URL`


