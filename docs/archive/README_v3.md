# ATS Resume Agent

## Overview

ATS Resume Agent is a FastAPI-based web service that uses AI to rewrite resume bullets to be ATS-friendly, impact-focused, and aligned with job descriptions. The application processes resume bullets through a 6-stage state machine pipeline that extracts job description signals, rewrites bullets using LLM calls, validates the output, and provides scoring metrics.

The system is designed for both individual resume processing and bulk B2B candidate evaluation against a single job description.

## Features (Code-verified only)

- **Resume Bullet Processing**: Rewrites up to 20 resume bullets per job with configurable tone and length limits
- **File Upload Support**: Basic file upload via UploadFile parameter with text extraction
- **Job Description Analysis**: Extracts keywords, skills, and tools from job descriptions using hybrid local NLP + LLM approach
- **Bulk Processing**: Processes multiple candidates against a single job description (up to 50 candidates per batch)
- **Real-time API**: FastAPI-based REST API with async processing and job status tracking
- **Security Controls**: Input sanitization, rate limiting, cost controls, and security monitoring
- **Caching**: Redis-based caching for job description parsing results to reduce LLM costs
- **Multi-LLM Support**: Supports both OpenAI (GPT-4) and Anthropic (Claude) models
- **Validation**: PII detection, factual consistency checking, and grammar validation

## Architecture

The application follows a multi-agent architecture with these core components:

### State Machine Pipeline (6 stages)
1. **INGEST**: Normalizes job description text and resume bullets, computes JD hash
2. **EXTRACT_SIGNALS**: Parses JD using hybrid approach (spaCy + TF-IDF + LLM fallback)
3. **PROCESS**: Batch rewrites bullets using fused processor (single LLM call for efficiency)
4. **VALIDATE**: Checks for PII, factual consistency, and applies safe fixes
5. **OUTPUT**: Assembles final results with coverage analysis
6. **COMPLETED**: Returns structured output with scores and validation flags

### Core Agents
- **JDParser**: Extracts keywords, soft skills, hard tools, and domain terms from job descriptions
- **FusedProcessor**: Batch processes bullet rewriting and scoring in single LLM call (primary processor)
- **Rewriter**: Individual bullet rewriter (legacy, still initialized but not used in current pipeline)
- **Scorer**: Computes coverage analysis between revised bullets and JD requirements
- **Validator**: Validates output for PII, factual consistency, and quality issues

### Operational Components
- **CostController**: Tracks daily API costs and request limits ($100/day, 1000 requests default)
- **SecurityMonitor**: Tracks suspicious activity, failed requests, and rate limiting
- **InputSanitizer**: Prevents prompt injection and XSS attacks
- **RedisCache**: Caches JD parsing results to avoid redundant LLM calls

## Setup & Installation

### Prerequisites
- Python 3.11+ (tested up to 3.13)
- Redis server (optional, falls back to no-op cache if unavailable)
- spaCy English model: `python -m spacy download en_core_web_sm`
- Document parsing libraries: python-docx, pdfplumber, chardet (for file upload support)

### Installation
```bash
# Clone repository
git clone <repository-url>
cd ATS_Resume_Agent

# Install dependencies
pip install -e .

# For development tools
pip install -e .[dev]
```

### Environment Variables
Required:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: LLM provider API key
- `LLM_PROVIDER`: "openai" or "anthropic" (default: "openai")
- `LLM_MODEL`: Model name (default: "gpt-4-turbo-preview" for OpenAI, "claude-3-5-sonnet-20241022" for Anthropic)

Optional:
- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379")
- `JD_CACHE_TTL`: Cache TTL in seconds (default: 3600)
- `MAX_DAILY_COST`: Daily cost limit in USD (default: 100.0)
- `MAX_REQUESTS_PER_DAY`: Daily request limit (default: 1000)
- `SPACY_CONFIDENCE_THRESHOLD`: Confidence threshold for local JD parsing (default: 0.7)
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated, default: localhost:3000,3001)

## Running the Application

### Development Server
```bash
# Start API server
python scripts/start_server.py
# or
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Production Deployment
```bash
# Using Docker
docker build -t ats-resume-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key ats-resume-agent

# Using Render (configured in render.yaml)
# Deploy via Render dashboard with environment variables
```

### CLI Usage
```bash
# Process resume from JSON file
python -m orchestrator.state_machine --input input.json --out result.json
```

## API / UI Overview

### REST Endpoints

**Health Check**
- `GET /health` - System health with cost warnings and security stats

**Individual Processing**
- `POST /api/resume/process` - Process single resume (async, supports file upload or text)
- `GET /api/resume/status/{job_id}` - Get job status
- `GET /api/resume/result/{job_id}` - Get job results
- `DELETE /api/resume/{job_id}` - Delete job

**Bulk Processing (B2B)**
- `POST /api/bulk/process` - Process multiple candidates against single JD
- `GET /api/bulk/status/{job_id}` - Get bulk job status
- `GET /api/bulk/results/{job_id}` - Get bulk job results

**Testing**
- `POST /api/test/process-sync` - Synchronous processing for testing

### Request/Response Format

**Individual Processing Request:**
```json
{
  "role": "Software Engineer",
  "jd_text": "Job description text...",
  "bullets": ["Bullet 1", "Bullet 2"],
  "extra_context": "Additional context",
  "settings": {
    "tone": "concise",
    "max_len": 30,
    "variants": 1
  }
}
```

**Bulk Processing Request:**
```json
{
  "job_description": "Job description text...",
  "candidates": [
    {
      "candidate_id": "candidate_1",
      "bullets": ["Bullet 1", "Bullet 2"]
    }
  ],
  "settings": {
    "tone": "concise",
    "max_len": 30
  }
}
```

## Data & Integrations

### External Systems
- **OpenAI API**: GPT-4 models for bullet rewriting and validation
- **Anthropic API**: Claude models as alternative LLM provider
- **Redis**: Caching layer for JD parsing results (optional)
- **spaCy**: Local NLP processing for job description analysis
- **scikit-learn**: TF-IDF analysis for keyword extraction
- **slowapi**: Rate limiting middleware for API endpoints

### Data Flow
1. Job description text → JDParser → Cached signals
2. Resume bullets + JD signals → FusedProcessor → Rewritten bullets with scores
3. Rewritten bullets → Validator → Quality-checked output
4. Results → Coverage analysis → Final structured output
5. Bulk processing uses BackgroundTasks for async candidate processing

## Security & Permissions

### Authentication
- No authentication required (public API)
- Rate limiting: 5 requests/minute per IP for processing endpoints, 100 requests/minute for health check
- Request size limit: 10MB maximum

### Security Controls
- **Input Sanitization**: HTML escaping, prompt injection prevention
- **Rate Limiting**: Dual system - slowapi decorators + custom rate limiter with per-IP limits and automatic cleanup
- **Cost Controls**: Daily cost and request limits with tracking
- **Security Monitoring**: Suspicious pattern detection and IP tracking
- **CORS**: Configurable allowed origins (default: localhost only)

### Data Protection
- PII detection (email, phone, SSN patterns)
- Factual consistency checking to prevent fabrication
- Input length limits (50KB JD, 1KB per bullet, 5KB context)

## Limitations & Known Unknowns

### Current Limitations
- **In-memory storage**: Job results stored in memory (not persistent across restarts)
- **No authentication**: Public API without user authentication
- **Single Redis instance**: No Redis clustering or failover
- **Limited bullet variants**: Maximum 3 variants per bullet (configurable)
- **Basic file upload**: UploadFile parameter extracts text only, no advanced resume parsing

### Configuration Assumptions
- spaCy model `en_core_web_sm` must be installed for optimal JD parsing
- Redis connection failures gracefully degrade to no-op cache
- LLM API keys must be valid and have sufficient quota
- Default cost limits may be insufficient for high-volume usage

### Potential Issues
- Debug print statements remain in production code (`api/main.py` lines 567, 569)
- No database persistence for job results or user data
- Limited error handling for LLM API failures
- No retry logic for failed LLM calls
- File upload extracts text only - no advanced parsing of resume formats

## Codebase Structure

```
ATS_Resume_Agent/
├── agents/                 # Core processing agents
│   ├── fused_processor.py  # Batch rewrite + score processor
│   ├── jd_parser.py       # Job description parser
│   ├── rewriter.py        # Individual bullet rewriter
│   ├── scorer.py          # Coverage analysis scorer
│   └── validator.py       # Output validation
├── api/                   # FastAPI web service
│   └── main.py           # API endpoints and middleware
├── orchestrator/          # State machine coordination
│   └── state_machine.py  # 6-stage processing pipeline
├── ops/                   # Operational utilities
│   ├── cost_controller.py # API cost tracking
│   ├── input_sanitizer.py # Security sanitization
│   ├── llm_client.py     # Multi-provider LLM client
│   ├── logging.py        # Structured logging
│   ├── redis_cache.py    # JD parsing cache
│   ├── security_monitor.py # Security event tracking
│   └── simple_rate_limiter.py # Rate limiting
├── schemas/               # Pydantic data models
│   └── models.py         # Input/output schemas
├── scripts/               # Utility scripts
│   ├── benchmark_pipeline.py # Performance testing
│   └── start_server.py   # Development server
├── tests/                 # Test suites
│   ├── api/              # API endpoint tests
│   ├── integration/      # End-to-end workflow tests
│   └── security/         # Security validation tests
├── pyproject.toml        # Project configuration
├── requirements.txt      # Dependencies
├── Dockerfile           # Container configuration
└── render.yaml          # Render.com deployment config
```

---

*All claims in this document are based strictly on code inspection.*
