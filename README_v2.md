# ATS Resume Engine

## Overview

**B2B Bulk Resume Processing API** powered by AI. Automatically rewrites candidate resume bullets to be ATS-friendly, impact-focused, and tightly aligned with job descriptions. The system processes multiple candidates against a single job description in batch operations.

**Core Functionality**: 
- Accepts manual text input (job description + resume bullets)
- Uses a 6-stage state machine pipeline to process bullets
- Returns revised bullets with JD alignment scores, impact scores, and coverage metrics
- Provides bulk processing for 1-50 candidates per batch
- Implements cost controls, rate limiting, and security monitoring

**Technology Stack**: Python 3.11+, FastAPI, OpenAI/Anthropic LLMs, Redis (optional), spaCy NLP, scikit-learn.

## Features (Code-verified)

### 1. 6-Stage State Machine Pipeline
**Location**: `orchestrator/state_machine.py`

The system executes in strict state sequence:
1. **INGEST**: Normalizes inputs, computes JD hash for caching, categorizes bullets
2. **EXTRACT_SIGNALS**: Parses JD using hybrid NLP (spaCy + TF-IDF + LLM fallback) with Redis caching
3. **PROCESS**: Batch rewrites bullets using fused processor (rewrite + score in single LLM call)
4. **VALIDATE**: Checks PII, factual consistency, grammar using LanguageTool
5. **OUTPUT**: Assembles results with coverage analysis
6. **COMPLETED**: Returns structured JSON response

### 2. Bulk Processing API
**Location**: `api/main.py` - `/api/bulk/process` endpoint

- Accepts up to 50 candidates per request (`schemas/models.py:202`)
- Each candidate can have 1-20 bullets (`schemas/models.py:196`)
- Background processing with job status tracking
- Returns job_id for status polling

### 3. Hybrid JD Parsing
**Location**: `agents/jd_parser.py`

- **Local extraction**: Uses spaCy NER and TF-IDF for fast processing
- **Confidence threshold**: Uses LLM only when confidence < 0.7 (`jd_parser.py:78`)
- **Redis caching**: Caches extracted signals by JD hash with 1-hour TTL (`ops/redis_cache.py:22`)
- **Categorization**: Extracts soft_skills, hard_tools, domain_terms for targeted rewriting

### 4. Fused Processor
**Location**: `agents/fused_processor.py`

Processes all bullets in a single LLM call (batch operation):
- Combines rewrite + scoring in one prompt
- Returns structured BulletResult with relevance/impact/clarity scores
- Graceful fallback on LLM failures

### 5. Input Sanitization & Security
**Location**: `ops/input_sanitizer.py`, `ops/security_monitor.py`

- Detects 18+ injection patterns including "ignore all previous instructions", "system prompt", "javascript:"
- HTML escapes all inputs to prevent XSS
- Tracks suspicious IP activity, failed requests, high request rates
- Logs security events with IP tracking

### 6. Cost Controls
**Location**: `ops/cost_controller.py`

- Daily cost limits (default: $100/day, configurable via `MAX_DAILY_COST`)
- Request count limits (default: 1000/day, configurable via `MAX_REQUESTS_PER_DAY`)
- Per-model cost estimation (gpt-4o-mini: $0.01, gpt-4-turbo: $0.05, gpt-4: $0.10)
- Blocks requests when limits exceeded

### 7. Rate Limiting
**Location**: `ops/simple_rate_limiter.py`, SlowAPI decorators

- Global rate limit: 5 requests/minute per IP for processing endpoints (`api/main.py:287`)
- Health check rate limit: 100 requests/minute (`api/main.py:233`)
- Request size limit: 10MB max (`api/main.py:84`)
- In-memory IP tracking with automatic cleanup

### 8. Validation System
**Location**: `agents/validator.py`

Checks for:
- PII detection (email, phone, SSN via regex patterns)
- Factual consistency (prevents invented tools/metrics via LLM)
- Active voice violations, filler phrases
- Hard tool fabrication (flags added tools not in original)

## Architecture

### Directory Structure

```
ATS_Resume_Agent/
├── agents/                      # AI agent components
│   ├── jd_parser.py            # JD signal extraction (hybrid: local + LLM)
│   ├── fused_processor.py      # Batch rewrite + score processor
│   ├── rewriter.py             # Individual bullet rewriter (legacy)
│   ├── scorer.py               # Coverage analysis and scoring
│   └── validator.py            # PII detection, factual consistency
├── orchestrator/                # State machine orchestration
│   └── state_machine.py        # 6-stage pipeline execution
├── ops/                         # Operational utilities
│   ├── llm_client.py           # Multi-provider LLM client (OpenAI, Anthropic)
│   ├── redis_cache.py          # JD signal caching
│   ├── cost_controller.py      # Daily cost and request limits
│   ├── input_sanitizer.py      # Security sanitization
│   ├── security_monitor.py     # Suspicious activity tracking
│   ├── simple_rate_limiter.py  # In-memory rate limiting
│   ├── logging.py              # Structured logging
│   └── ulid_gen.py             # Job ID generation
├── schemas/                     # Data models
│   └── models.py               # Pydantic models (JobInput, JobOutput, BulletResult, etc.)
├── api/                         # REST API
│   └── main.py                 # FastAPI app with endpoints
├── scripts/                     # Utility scripts
│   ├── start_server.py         # Start server for testing
│   └── benchmark_pipeline.py   # Performance benchmarking
└── tests/                       # Test suite
    ├── api/                    # API endpoint tests
    ├── integration/            # Integration tests
    └── security/               # Security tests
```

### Request Flow

```
Client Request
    ↓
FastAPI API Layer (rate limit, sanitize, security headers)
    ↓
State Machine Orchestrator
    ↓
1. INGEST: Normalize inputs, hash JD
    ↓
2. EXTRACT_SIGNALS: Check Redis cache → local extraction → LLM if needed
    ↓
3. PROCESS: Batch rewrite all bullets with fused processor
    ↓
4. VALIDATE: Check PII, factual consistency, grammar
    ↓
5. OUTPUT: Assemble results with coverage metrics
    ↓
6. COMPLETED: Return JobOutput JSON
```

### Component Interactions

**LLM Client** (`ops/llm_client.py`):
- Supports OpenAI and Anthropic providers
- Auto-selects based on `LLM_PROVIDER` env var (default: openai)
- Configurable temperature, max_tokens per call
- Wraps JSON parsing for structured responses

**Redis Cache** (`ops/redis_cache.py`):
- Caches JD signals by hash with 1-hour TTL
- Gracefully falls back to no-op if Redis unavailable
- Uses `REDIS_URL` env var (default: redis://localhost:6379)

**Security Monitor** (`ops/security_monitor.py`):
- Tracks failed requests per IP (max 10/hour)
- Detects high request rates (max 20/minute per IP)
- Logs suspicious patterns to operations logs

**Cost Controller** (`ops/cost_controller.py`):
- Tracks daily costs by date in-memory
- Cleans up data older than 7 days
- Estimates costs per model before allowing requests

## Setup & Installation

### Prerequisites
- Python 3.11+ (3.12, 3.13 supported; 3.14 blocked by `pyproject.toml:15`)
- Redis (optional, for caching)
- OpenAI API key OR Anthropic API key

### Installation Steps

1. **Clone repository**
```bash
git clone <repository-url>
cd ATS_Resume_Agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm  # Required for local JD parsing
```

3. **Configure environment**
Create `.env` file:
```bash
# LLM Provider (required)
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-...

# Model configuration
LLM_MODEL=gpt-4o-mini  # Default model
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# Optional: Redis caching
REDIS_URL=redis://localhost:6379/0
JD_CACHE_TTL=3600

# Optional: Cost controls
MAX_DAILY_COST=100.0
MAX_REQUESTS_PER_DAY=1000

# Optional: CORS configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Optional: NLP confidence threshold
SPACY_CONFIDENCE_THRESHOLD=0.7
```

4. **Run server**
```bash
# Development
uvicorn api.main:app --reload

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Or use script
python scripts/start_server.py
```

Server runs at `http://localhost:8000`

## Running the Application

### Primary Endpoint: Bulk Processing

**POST** `/api/bulk/process`

Process multiple candidates against a single job description.

**Request:**
```json
{
  "job_description": "We are seeking a Senior Software Engineer with Python experience...",
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "bullets": [
        "Built web applications using Python and Django",
        "Led team of 5 developers on agile projects"
      ]
    },
    {
      "candidate_id": "candidate_002",
      "bullets": [
        "Managed database operations and CI/CD pipelines"
      ]
    }
  ],
  "settings": {
    "tone": "professional",
    "max_len": 30,
    "variants": 1
  }
}
```

**Response:**
```json
{
  "job_id": "01K8E9S9MFEQAQFPGX3RJG6ZA8",
  "status": "processing",
  "total_candidates": 2,
  "processed_candidates": 0,
  "candidates": []
}
```

**Status Tracking:**
- `GET /api/bulk/status/{job_id}` - Check processing status
- `GET /api/bulk/results/{job_id}` - Get results when complete (returns 202 if still processing)

**Complete Result Example:**
```json
{
  "job_id": "01K8E9S9MFEQAQFPGX3RJG6ZA8",
  "status": "completed",
  "total_candidates": 2,
  "processed_candidates": 2,
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "status": "completed",
      "results": [
        {
          "original": "Built web applications using Python and Django",
          "revised": ["Developed scalable web applications with Python and Django, achieving 40% performance improvement"],
          "scores": {
            "relevance": 92,
            "impact": 85,
            "clarity": 95
          },
          "notes": "Enhanced with quantifiable outcome and ATS keywords",
          "diff": {
            "removed": [],
            "added_terms": ["scalable", "achieving", "performance improvement"]
          }
        }
      ],
      "coverage": {
        "hit": ["Python", "Django", "web applications"],
        "miss": ["AWS", "microservices"]
      }
    }
  ]
}
```

### Testing Endpoint

**POST** `/api/resume/process` (Testing/Dev only)

Single resume processing with manual text input via form data:
- `resume_text`: Newline-separated bullets
- `role`: Target role
- `jd_text`: Job description text
- `extra_context`: Optional context

**Rate Limited**: 5 requests/minute per IP

### Health Check

**GET** `/health`

Returns system status, active jobs, cost warnings, security stats:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "active_jobs": 3,
  "cost_warnings": [],
  "security": {
    "suspicious_ips": [],
    "total_failed_attempts": 0,
    "total_suspicious_patterns": 0
  }
}
```

## API / UI Overview

**Endpoints (verified in code):**

1. **POST `/api/bulk/process`** - Primary bulk processing endpoint
2. **GET `/api/bulk/status/{job_id}`** - Check bulk job status
3. **GET `/api/bulk/results/{job_id}`** - Get bulk job results
4. **POST `/api/resume/process`** - Single resume processing (testing)
5. **GET `/api/resume/status/{job_id}`** - Check single job status
6. **GET `/api/resume/result/{job_id}`** - Get single job result
7. **DELETE `/api/resume/{job_id}`** - Delete a job
8. **POST `/api/test/process-sync`** - Synchronous processing (testing)
9. **GET `/health`** - Health check
10. **GET `/docs`** - Interactive Swagger UI (FastAPI auto-generated)
11. **GET `/redoc`** - ReDoc documentation

**Rate Limits:**
- Bulk processing: 5 requests/minute
- Health check: 100 requests/minute
- Request size: 10MB max

## Data & Integrations

### External Systems

**LLM Providers:**
- OpenAI API (models: gpt-4-turbo-preview, gpt-4o-mini, gpt-4)
- Anthropic API (claude-3-5-sonnet-20241022)
- Provider selected via `LLM_PROVIDER` env var

**Caching:**
- Redis for JD signal caching (optional, falls back to no-op)
- Cache key format: `jd_signals:{hash}`
- TTL: 1 hour (configurable via `JD_CACHE_TTL`)

**NLP Processing:**
- spaCy for named entity recognition and text processing
- scikit-learn for TF-IDF vectorization and cosine similarity
- Pattern matching for technology keywords and soft skills

### Data Models

**JobInput** (`schemas/models.py:33`):
- `role`: Target role (max 200 chars)
- `jd_text`: Job description (max 50KB)
- `bullets`: List of bullets (1-20 items, 1000 chars each)
- `extra_context`: Optional context (max 5KB)
- `settings`: Tone, max_len, variants

**JobOutput** (`schemas/models.py:110`):
- `job_id`: ULID job identifier
- `summary`: Role, top terms, coverage
- `results`: List of BulletResult objects
- `red_flags`: Validation issues
- `logs`: Execution log entries

**BulletResult** (`schemas/models.py:76`):
- `original`: Original bullet text
- `revised`: List of revised variants (typically 1)
- `scores`: Relevance/impact/clarity (0-100 each)
- `notes`: Explanation of changes
- `diff`: Added/removed terms

## Security & Permissions

### Authentication
**Code indicates**: No authentication layer implemented (`api/main.py` has no auth decorators or middleware). All endpoints are publicly accessible.

**Security controls implemented:**
- Rate limiting (5 req/min per IP)
- Input sanitization (18+ patterns, HTML escaping)
- Request size limits (10MB)
- PII detection (email, phone, SSN)
- Cost controls (daily limits)
- Security monitoring (suspicious IP tracking)

### Security Headers
**Location**: `api/main.py:113-124`

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### CORS Configuration
**Location**: `api/main.py:51-59`

- Configurable via `ALLOWED_ORIGINS` env var
- Development default: `http://localhost:3000`, `http://localhost:3001`
- Credentials allowed

### Input Sanitization
**Location**: `ops/input_sanitizer.py`

Detects and filters:
- Prompt injection patterns ("ignore all previous instructions", "system prompt", etc.)
- JavaScript injection attempts
- HTML/script tags
- Suspicious repetition patterns

### Security Monitoring
**Location**: `ops/security_monitor.py`

Tracks:
- Failed requests per IP (flags after 10/hour)
- Request rate per IP (flags after 20/minute)
- Suspicious patterns detected in inputs
- Exposes security stats in `/health` endpoint

## Limitations & Known Unknowns

### Stated Limitations (from code comments)

**Storage**: In-memory job storage - results lost on restart (`api/main.py:90`)
**Authentication**: No user auth implemented (`api/main.py` - no auth decorators)
**Redis**: Optional, falls back gracefully if unavailable (`ops/redis_cache.py:30`)
**Dependencies**: Requires spaCy model download separately (`jd_parser.py:102`)

### Processing Constraints (from schema validators)

**Maximum candidates per bulk request**: 50 (`schemas/models.py:202`)
**Maximum bullets per candidate**: 20 (`schemas/models.py:196`)
**Maximum bullet length**: 1000 characters (`schemas/models.py:196`)
**Maximum JD length**: 50,000 characters (`schemas/models.py:16`)
**Maximum role length**: 200 characters (`schemas/models.py:15`)
**Maximum extra context**: 5,000 characters (`schemas/models.py:17`)

### Configuration Assumptions

**Environment Variables:**
- `.env` file loading is done in `state_machine.py:9` via `load_dotenv()`
- Default CORS origins for localhost:3000, 3001
- Default cost limits: $100/day, 1000 requests/day
- Default LLM temperature: 0.3
- Default model: gpt-4o-mini for OpenAI, claude-3-5-sonnet for Anthropic

**Redis Behavior:**
- Connects to `redis://localhost:6379` if `REDIS_URL` not set
- Cache TTL defaults to 3600 seconds (1 hour)
- Falls back to no-op cache if connection fails (logs warning but continues)

**Error Handling:**
- LLM failures in batch processing fall back to preserving original bullets (`agents/fused_processor.py:150`)
- Redis connection failures are logged but don't block processing (`ops/redis_cache.py:30`)
- LanguageTool unavailable → skips grammar checking (assumed, not verified in code)

### Uncertain/Ambiguous Behavior

**LanguageTool Integration**: Code references LanguageTool for grammar checking (`IMPLEMENTATION_SUMMARY.md` mentions it) but validator code (`agents/validator.py`) only shows PII and factual consistency checks. Grammar checking behavior is unclear.

**Redis Failover**: Code assumes Redis is optional and gracefully degrades, but doesn't specify how job results persist across instances in a multi-instance deployment.

**Rate Limiting Distribution**: In-memory rate limiting won't work across multiple API instances. No Redis-backed rate limiter found in code.

**Docker Production**: Dockerfile exists but no docker-compose.yml or production deployment config. Deployment pattern uncertain.

## Codebase Structure (High-Level)

### Entry Points
- **API Server**: `api/main.py:641` - `if __name__ == "__main__"`
- **CLI State Machine**: `orchestrator/state_machine.py:365` - `main()`
- **Server Script**: `scripts/start_server.py:4`

### Primary Workflows

1. **Bulk Processing**: Client → `POST /api/bulk/process` → background task → StateMachine.execute() → Results stored in `jobs_storage` dict → Client polls status
2. **Single Processing**: Client → `POST /api/resume/process` → background task → StateMachine.execute() → Results stored
3. **CLI Processing**: Command line → StateMachine.main() → reads JSON input → executes → writes JSON output

### Key Dependencies (from pyproject.toml)

**Core:**
- fastapi>=0.109.0 (REST API)
- uvicorn (ASGI server)
- pydantic>=2.6.0 (validation)
- python-dotenv>=1.0.0 (config)
- python-ulid>=2.2.0 (IDs)

**LLM:**
- openai>=1.12.0
- anthropic>=0.18.0

**NLP:**
- spacy>=3.7.0
- scikit-learn>=1.3.0

**Caching:**
- redis>=5.0.0

**Testing:**
- pytest>=8.0.0
- pytest-asyncio>=0.23.4

---

*All claims in this document are based strictly on code inspection of the ATS Resume Agent codebase as of the audit date. No assumptions were made about undocumented behavior or future features.*
