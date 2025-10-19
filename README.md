# ATS Resume Bullet Revisor

> **AI-powered resume optimization service** that rewrites resume bullets to be ATS-friendly, impact-focused, and tightly aligned to job descriptions—without fabricating facts.

---

## Overview

The **ATS Resume Bullet Revisor** is a production-ready, multi-agent AI system built to help job seekers optimize their resumes for Applicant Tracking Systems (ATS). It analyzes job descriptions, extracts priority keywords, and intelligently rewrites resume bullets to maximize relevance while preserving factual accuracy.

Unlike simple keyword stuffing, this system:
- **Prevents fabrication**: Never adds tools, metrics, or achievements that weren't in the original bullet
- **Categorizes keywords**: Distinguishes between soft skills (inferred), hard tools (factual), and domain terms (contextual)
- **Scores variants**: Evaluates on relevance (JD alignment), impact (outcomes), and clarity (conciseness)
- **Validates output**: Checks for PII, passive voice, filler phrases, and unsupported claims
- **Provides transparency**: Returns coverage analysis, change rationale, and red flags

**Target Users**: Job seekers, career coaches, resume writing services, and developers building resume tools.

---

## Core Features

### 🎯 Multi-Agent Architecture
- **JD_PARSER**: Extracts and categorizes keywords from job descriptions (soft skills, hard tools, domain terms)
- **REWRITER**: Rewrites bullets using role-appropriate terminology while preserving facts
- **SCORER**: Scores variants on relevance (0-100), impact (0-100), and clarity (0-100)
- **VALIDATOR**: Checks for grammar issues, PII, passive voice, and fabrication

### 🔄 Durable State Machine
- **6-stage workflow**: INGEST → EXTRACT_SIGNALS → REWRITE → SCORE_SELECT → VALIDATE → OUTPUT
- **Idempotency**: Safe retries with job_id correlation
- **Structured logging**: JSON logs with timestamps and stage tracking

### 🚀 Production-Ready REST API
- **FastAPI** framework with async background job processing
- **Rate limiting**: SlowAPI + custom rate limiter to prevent abuse
- **Security hardening**: Input sanitization, request size limits (10MB), security headers
- **Cost control**: Daily limits on LLM API costs and request counts
- **CORS support**: Ready for frontend integration (React/Next.js)

### 🛡️ Anti-Fabrication Guardrails
- **Metrics rule**: Only use metrics from the specific bullet being edited
- **Tools rule**: Never add tools/platforms not mentioned in the original
- **Activity rule**: Preserve core activity type (research stays research, not marketing)
- **LLM-powered validation**: Detects hard tool fabrication, borrowed metrics, and activity mismatches

### 📊 Intelligent Analysis
- **Coverage tracking**: Shows which JD terms are hit/miss across all bullets
- **Keyword categorization**: Soft skills (add if demonstrated), hard tools (never fabricate), domain terms (context-dependent)
- **Multiple variants**: Generates 2-5 variants per bullet with rationale
- **Red flags**: Alerts for PII, passive phrasing, vague outcomes, and unsupported claims

---

## Architecture Summary

### Tech Stack
- **Language**: Python 3.11+
- **API Framework**: FastAPI + Uvicorn
- **LLM Providers**: OpenAI (GPT-4o-mini, GPT-4) or Anthropic (Claude 3.5 Sonnet)
- **Validation**: Pydantic v2 for schema validation
- **ID Generation**: ULID for job tracking
- **Retry Logic**: Tenacity with exponential backoff
- **Document Parsing**: pdfplumber, python-docx, BeautifulSoup4 (for JD scraping)
- **Containerization**: Docker with multi-stage builds
- **Deployment**: Render.com (web service)

### Project Structure
```
ats-resume-agent/
├── agents/                    # Multi-agent system
│   ├── jd_parser.py          # Job description keyword extraction
│   ├── rewriter.py           # Bullet rewriting with anti-fabrication rules
│   ├── scorer.py             # Relevance/impact/clarity scoring
│   └── validator.py          # Grammar, PII, and fabrication checks
├── api/
│   └── main.py               # FastAPI REST API with security controls
├── orchestrator/
│   ├── state_machine.py      # 6-stage workflow orchestrator
│   └── idempotency.py        # Idempotency key management
├── ops/                      # Operational utilities
│   ├── llm_client.py         # Unified OpenAI/Anthropic client
│   ├── logging.py            # Structured JSON logging
│   ├── cost_controller.py    # API cost limits and tracking
│   ├── security_monitor.py   # Suspicious activity detection
│   ├── input_sanitizer.py    # Input validation and sanitization
│   ├── retry.py              # Retry logic with backoff
│   ├── hashing.py            # JD hash computation
│   └── ulid_gen.py           # ULID generation
├── schemas/
│   └── models.py             # Pydantic models for I/O and state
├── Dockerfile                # Multi-stage production build
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Package metadata and tool configs
└── render.yaml               # Deployment configuration
```

### Data Flow
1. **User submits**: Role, JD (text or URL), resume bullets
2. **API creates job**: Generates ULID, queues background task
3. **State machine executes**:
   - Ingests JD and normalizes bullets
   - Extracts categorized keywords (soft skills, hard tools, domain terms)
   - Rewrites bullets with JD alignment
   - Scores variants on relevance/impact/clarity
   - Validates for quality and fabrication
4. **API returns**: Job ID, revised bullets, scores, coverage, red flags

---

## Setup Instructions

### Prerequisites
- Python 3.11+ (tested on 3.11-3.13)
- OpenAI API key OR Anthropic API key
- (Optional) Docker for containerized deployment

### Local Development Setup

#### 1. Clone and Install Dependencies
```bash
# Clone the repository (or download the source)
cd ATS_Resume_Agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# OR for development with testing tools
pip install -e .[dev]
```

#### 2. Configure Environment Variables
```bash
# Copy example environment file
cp env.example .env

# Edit .env with your API key
# Required:
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=your-key-here

# Optional configuration:
LLM_PROVIDER=openai               # or "anthropic"
LLM_MODEL=gpt-4o-mini             # or "gpt-4-turbo-preview" or "claude-3-5-sonnet-20241022"
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# Cost/rate limits:
MAX_DAILY_COST=100.0              # Max $100/day in LLM costs
MAX_REQUESTS_PER_DAY=1000         # Max 1000 requests/day
RATE_LIMIT_REQUESTS_PER_MINUTE=10

# Security:
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### 3. Run the API Server
```bash
# Start the server (development mode)
python start_server.py

# The API will be available at:
# http://localhost:8000
# Docs: http://localhost:8000/docs
```

#### 4. Test the Workflow
```bash
# Run full workflow test (requires API key)
python test_full_workflow.py

# Test API endpoint
python test_api_simple.py

# Run CLI state machine directly
python -m orchestrator.state_machine --input test_request.json --out out/result.json
```

### Docker Deployment

#### Build and Run Container
```bash
# Build image
docker build -t ats-resume-agent .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e LLM_PROVIDER=openai \
  -e LLM_MODEL=gpt-4o-mini \
  ats-resume-agent
```

### Deploy to Render.com

The application is pre-configured for Render deployment via `render.yaml`:

1. Push code to GitHub
2. Create new Web Service on Render.com
3. Connect your GitHub repository
4. Add environment variable: `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`)
5. Deploy (uses `render.yaml` config automatically)

**Note**: Free tier on Render will spin down after inactivity. Consider upgrading for production workloads.

---

## Configuration

### Required Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative) | `sk-ant-...` |

### Optional Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4-turbo-preview` | Model name (see docs for options) |
| `LLM_TEMPERATURE` | `0.3` | LLM temperature (0.0-1.0) |
| `LLM_MAX_TOKENS` | `2000` | Max tokens per LLM call |
| `MAX_DAILY_COST` | `100.0` | Max daily LLM cost in USD |
| `MAX_REQUESTS_PER_DAY` | `1000` | Max API requests per day |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `10` | Rate limit per IP |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment name |

### Supported LLM Models

**OpenAI:**
- `gpt-4o-mini` (recommended for cost/speed balance)
- `gpt-4-turbo-preview`
- `gpt-4`

**Anthropic:**
- `claude-3-5-sonnet-20241022` (recommended)
- `claude-3-opus-20240229`

---

## Example Usage

### REST API (Recommended)

#### 1. Process Resume (Async)
```bash
# Submit job
curl -X POST http://localhost:8000/api/resume/process \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Senior Software Engineer",
    "jd_text": "We seek a Senior Engineer with Python, FastAPI, AWS experience...",
    "bullets": [
      "Built REST APIs using Python",
      "Deployed apps to cloud infrastructure"
    ],
    "settings": {
      "max_len": 30,
      "variants": 2
    }
  }'

# Response: {"job_id": "01HQ...", "status": "queued", ...}

# Check status
curl http://localhost:8000/api/resume/status/{job_id}

# Get results
curl http://localhost:8000/api/resume/result/{job_id}
```

#### 2. Process Resume (Sync - for testing)
```bash
curl -X POST http://localhost:8000/api/test/process-sync \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Marketing Manager",
    "jd_text": "Seeking Marketing Manager with B2B SaaS experience, Marketo expertise...",
    "bullets": [
      "Managed email campaigns for product launches"
    ],
    "settings": {"max_len": 30, "variants": 2}
  }'
```

**Response Structure:**
```json
{
  "job_id": "01HQ...",
  "summary": {
    "role": "Marketing Manager",
    "top_terms": ["B2B SaaS", "Marketo", "demand generation", ...],
    "coverage": {
      "hit": ["email campaigns", "product launches"],
      "miss": ["Marketo", "demand generation"]
    }
  },
  "results": [
    {
      "original": "Managed email campaigns for product launches",
      "revised": [
        "Led multi-channel product launch campaigns, applying analytical thinking to optimize messaging and timing for B2B audiences",
        "Orchestrated email-driven product launches with data-informed segmentation, enhancing campaign performance and reach"
      ],
      "scores": {
        "relevance": 85,
        "impact": 78,
        "clarity": 92
      },
      "notes": "Added 'analytical thinking' soft skill; kept original activity (email campaigns); avoided fabricating Marketo since not in original",
      "diff": {
        "removed": [],
        "added_terms": ["analytical thinking", "B2B", "data-informed"]
      }
    }
  ],
  "red_flags": [],
  "logs": [...]
}
```

### CLI (Command Line)

```bash
# Create input file
cat > my_resume.json << EOF
{
  "role": "Data Analyst",
  "jd_text": "Seeking Data Analyst with SQL, Python, Tableau experience...",
  "bullets": [
    "Analyzed customer data to identify trends",
    "Created dashboards for business stakeholders"
  ],
  "settings": {"max_len": 30, "variants": 2}
}
EOF

# Run state machine
python -m orchestrator.state_machine \
  --input my_resume.json \
  --out result.json

# View results
cat result.json | jq '.results[0].revised'
```

### Python SDK

```python
from orchestrator.state_machine import StateMachine
from schemas.models import JobInput, JobSettings

# Initialize
sm = StateMachine()

# Create input
job_input = JobInput(
    role="Product Manager",
    jd_text="Seeking PM with roadmap planning, Agile, Jira experience...",
    bullets=[
        "Planned product roadmaps for 3 features",
        "Coordinated with engineering teams"
    ],
    settings=JobSettings(max_len=30, variants=2)
)

# Execute
result = sm.execute(job_input.model_dump())

# Access results
for bullet_result in result['results']:
    print(f"Original: {bullet_result['original']}")
    print(f"Revised: {bullet_result['revised'][0]}")
    print(f"Scores: {bullet_result['scores']}")
```

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `GET` | `/` | Health check | N/A |
| `GET` | `/health` | Detailed health + cost stats | 100/min |
| `POST` | `/api/resume/process` | Submit job (async) | 5/min |
| `GET` | `/api/resume/status/{job_id}` | Check job status | N/A |
| `GET` | `/api/resume/result/{job_id}` | Get job results | N/A |
| `DELETE` | `/api/resume/{job_id}` | Delete job | N/A |
| `POST` | `/api/test/process-sync` | Sync processing (testing only) | 5/min |

### Interactive API Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Security Features

### Input Validation & Sanitization
- **Field length limits**: Role (200), JD (50KB), bullets (20 max, 1KB each), context (5KB)
- **HTML/script stripping**: Removes malicious tags
- **Pattern detection**: Flags SQL injection, XSS, path traversal attempts
- **Pydantic validation**: Schema enforcement on all inputs

### Rate Limiting
- **Global**: 5 requests/min on expensive operations
- **Custom**: Configurable per-IP tracking with cleanup
- **SlowAPI**: Memory-based rate limiter with 429 responses

### Cost Control
- **Daily limits**: Max cost (default $100) and request count (default 1000)
- **Tracking**: Per-model cost estimation and logging
- **Warnings**: Alerts at 80% of limits

### Security Monitoring
- **Failed requests**: Tracks failures per IP (max 10/hour)
- **Suspicious patterns**: Detects anomalies in input
- **Request rates**: Flags high-volume IPs (20/min threshold)
- **Health endpoint**: Returns suspicious IP count and reasons

### Response Security
- **Headers**: X-Content-Type-Options, X-Frame-Options, HSTS, CSP
- **Error sanitization**: Generic error messages (no stack traces)
- **Request size limit**: 10MB max body size

### Docker Security
- **Non-root user**: Runs as `appuser` (UID 1000)
- **Minimal base**: Python 3.11-slim with only required packages
- **Health checks**: Built-in container health monitoring

---

## Development

### Running Tests
```bash
# Install dev dependencies
pip install -e .[dev]

# Run full workflow test (requires API key)
python test_full_workflow.py

# Test API
python test_api_simple.py

# Manual API test
python test_api_manual.py
```

### Code Quality Tools
```bash
# Linting (Ruff)
ruff check .

# Formatting (Black)
black .

# Type checking (MyPy)
mypy .

# Security scanning (Bandit)
bandit -r agents orchestrator ops schemas api
```

### Project Scripts
- `start_server.py` - Start FastAPI development server
- `test_full_workflow.py` - End-to-end workflow test with real LLM calls
- `test_api_simple.py` - Quick API health check
- `penetration_tests.py` - Security testing suite
- `run_security_tests.py` - Automated security validation

---

## Troubleshooting

### API Key Issues
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### LLM Timeout
- Default timeout: 30s per request
- Increase with: `LLM_TIMEOUT=60` in `.env`
- Or switch to faster model: `LLM_MODEL=gpt-4o-mini`

### Rate Limit Errors (429)
- Check current usage: `GET /health`
- Adjust limits in `.env`: `MAX_REQUESTS_PER_DAY=2000`
- Or wait for daily reset (midnight UTC)

### Cost Limit Reached
- Check daily cost: `GET /health` → `cost_warnings`
- Increase limit: `MAX_DAILY_COST=200.0`
- Or wait for daily reset

### Docker Build Fails
```bash
# Clear cache and rebuild
docker system prune -a
docker build --no-cache -t ats-resume-agent .
```

---

## Limitations & Known Issues

### Current Limitations
1. **In-memory storage**: Job results stored in memory (lost on restart). Use Redis/PostgreSQL for production persistence.
2. **No authentication**: API is open (add JWT/API key auth for production).
3. **JD URL scraping**: Simple HTML fetch; may fail on JavaScript-heavy pages (manual JD input supported).
4. **Single instance**: No horizontal scaling (add Redis for distributed rate limiting).
5. **Cost tracking**: Per-instance only (doesn't aggregate across multiple deployments).

### Planned Enhancements
- [ ] Redis integration for job storage and rate limiting
- [ ] Authentication layer (API keys or JWT)
- [ ] Enhanced JD scraping with Playwright/Selenium
- [ ] PDF/DOCX resume parsing (currently text-only)
- [ ] Webhook callbacks for async job completion
- [ ] Admin dashboard for cost/usage monitoring

---

## License

**MIT License**

This project is open-source software. You are free to use, modify, and distribute it under the terms of the MIT License. See source code for full license text.

---

## Contributing

This is a production-ready template/reference implementation. For contributions:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code quality standards (Ruff, Black, MyPy)
4. Add tests for new features
5. Submit pull request

---

## Credits

**Built by**: ATS Resume Agent Team

**Technologies**: FastAPI, OpenAI/Anthropic, Pydantic, Docker

**Inspiration**: Designed to solve real-world ATS optimization challenges while preventing common fabrication issues in AI-powered resume tools.

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub (if repository is public)
- Check API documentation: http://localhost:8000/docs
- Review example files in repository root

---

**Version**: 1.0.0  
**Last Updated**: October 2024  
**Python**: 3.11+  
**Status**: Production-ready (Beta)

