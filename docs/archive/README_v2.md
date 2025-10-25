# ATS Resume Agent

## Overview

**B2B Resume Rewrite Engine** - A multi-agent AI system that processes batches of resumes against specific job descriptions quickly, reliably, and without fabrication. Designed for enterprise recruiters and ATS/CRM integration.

**Core Value Proposition**: Process multiple candidates' resumes against a single job description with structured validation data, providing measurable ROI for recruiters through bulk processing and JD alignment transparency.

The system uses a 6-stage state machine workflow to process resume bullets through ingestion, signal extraction, rewriting, scoring, validation, and output generation. Built as a FastAPI web service with comprehensive security controls, cost management, and caching mechanisms.

## Features (Code-verified only)

- **Multi-stage Pipeline**: 6-state workflow (INGEST → EXTRACT_SIGNALS → PROCESS → VALIDATE → OUTPUT → COMPLETED)
- **Hybrid JD Parsing**: Local NLP processing (spaCy + TF-IDF) with LLM fallback for job description analysis
- **Batch Processing**: Fused processor combines rewrite + score operations in single LLM calls for efficiency
- **Bulk Resume Processing**: Process multiple candidates against single job description via `/api/bulk/process`
- **Redis Caching**: JD signal extraction results cached to avoid redundant LLM calls
- **Security Controls**: Input sanitization, rate limiting, suspicious pattern detection, and security monitoring
- **Cost Management**: Daily cost and request limits with usage tracking
- **Multi-provider LLM Support**: OpenAI and Anthropic with unified client interface
- **PII Detection**: Automatic detection and flagging of personally identifiable information
- **Factual Consistency Checking**: LLM-based validation to prevent fabrication of hard tools/metrics
- **ULID Generation**: Unique, sortable job identifiers with timestamp encoding
- **Custom Exception Handling**: Structured error hierarchy for resume parsing failures

## Architecture

### Core Components

**State Machine Orchestrator** (`orchestrator/state_machine.py`)
- Manages the 6-stage workflow execution
- Handles state transitions and error recovery
- Coordinates between all agent components

**Agent Components** (`agents/`)
- `jd_parser.py`: Extracts keywords and signals from job descriptions using hybrid local/LLM approach
- `fused_processor.py`: Batch processes bullets with combined rewrite + score operations
- `rewriter.py`: Rewrites resume bullets for ATS optimization and JD alignment
- `scorer.py`: Scores bullet variants on relevance, impact, and clarity dimensions
- `validator.py`: Validates grammar, active voice, PII, and factual consistency

**Operational Infrastructure** (`ops/`)
- `llm_client.py`: Unified client for OpenAI/Anthropic API calls
- `redis_cache.py`: Caching layer for JD parsing results
- `input_sanitizer.py`: Security-focused input validation and sanitization
- `cost_controller.py`: API cost tracking and limit enforcement
- `security_monitor.py`: Suspicious activity detection and logging
- `logging.py`: Structured JSON logging with job correlation
- `retry.py`: Exponential backoff retry logic for external calls
- `ulid_gen.py`: ULID generation for unique, sortable job identifiers
- `simple_rate_limiter.py`: Fallback rate limiting implementation

**Data Models** (`schemas/models.py`)
- Pydantic models for input/output validation
- Job state management and internal data structures
- Comprehensive type definitions for all data flows
- Bulk processing models for B2B workflows

**API Layer** (`api/`)
- `main.py`: FastAPI application with REST endpoints
- CORS, rate limiting, and security middleware

### Execution Flow

1. **INGEST**: Resolve job description (URL or text), normalize content, compute hashes
2. **EXTRACT_SIGNALS**: Parse JD using hybrid approach (local NLP + LLM fallback), cache results
3. **PROCESS**: Batch rewrite + score bullets using fused processor
4. **VALIDATE**: Check grammar, active voice, PII, and factual consistency
5. **OUTPUT**: Assemble final results with coverage analysis
6. **COMPLETED**: Return structured output with scores and validation flags

## Setup & Installation

### Prerequisites
- Python 3.11+ (tested up to 3.13)
- Redis server (optional, for caching)
- LLM API key (OpenAI or Anthropic)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ATS_Resume_Agent

# Install dependencies
pip install -e .

# For development with additional tools
pip install -e .[dev]
```

### Environment Variables

**Required:**
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: LLM provider API key

**Optional Configuration:**
- `LLM_PROVIDER`: "openai" or "anthropic" (default: "openai")
- `LLM_MODEL`: Model name (default: "gpt-4-turbo-preview" for OpenAI, "claude-3-5-sonnet-20241022" for Anthropic)
- `LLM_TEMPERATURE`: Sampling temperature (default: 0.3)
- `LLM_MAX_TOKENS`: Maximum tokens per request (default: 2000)
- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379")
- `JD_CACHE_TTL`: Cache TTL in seconds (default: 3600)
- `MAX_DAILY_COST`: Daily cost limit in USD (default: 100.0)
- `MAX_REQUESTS_PER_DAY`: Daily request limit (default: 1000)
- `SPACY_CONFIDENCE_THRESHOLD`: Confidence threshold for local JD parsing (default: 0.7)
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated, defaults to localhost:3000, localhost:3001)

## Running the Application

### Development Server
```bash
# Start API server
python scripts/start_server.py
# Server runs on http://localhost:8000
```

### Production Deployment
```bash
# Using uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Using Docker
docker build -t ats-resume-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key ats-resume-agent
```

### CLI Usage
```bash
# Process resume bullets from JSON file
python -m orchestrator.state_machine --input input.json --out result.json

# Run full workflow test
python tests/integration/test_full_workflow.py

# Run performance benchmark
python scripts/benchmark_pipeline.py
```

## API / UI Overview

### REST Endpoints

**Core Processing:**
- `POST /api/bulk/process`: Process multiple candidates against single job description (B2B primary endpoint)
- `GET /api/bulk/status/{job_id}`: Check bulk job processing status
- `GET /api/bulk/results/{job_id}`: Retrieve bulk processing results
- `POST /api/resume/process`: Process single resume with job description (legacy endpoint)
- `GET /api/resume/status/{job_id}`: Check job processing status
- `GET /api/resume/result/{job_id}`: Retrieve completed results
- `DELETE /api/resume/{job_id}`: Delete job and results

**Testing/Development:**
- `POST /api/test/process-sync`: Synchronous processing for testing
- `GET /health`: Health check with cost and security stats

### B2B Integration

The API is designed for enterprise integration with ATS/CRM systems:

**Bulk Processing Workflow:**
1. Submit job description and candidate list via `POST /api/bulk/process`
2. Poll status via `GET /api/bulk/status/{job_id}` 
3. Retrieve results via `GET /api/bulk/results/{job_id}` when complete

**Request Format:**
```json
{
  "job_description": "Software Engineer role description...",
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "bullets": ["bullet1", "bullet2", "bullet3"]
    }
  ],
  "settings": {
    "max_len": 30,
    "variants": 1
  }
}
```

**Response Format:**
```json
{
  "job_id": "01HZ...",
  "status": "completed",
  "total_candidates": 10,
  "processed_candidates": 10,
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "status": "completed",
      "results": [...],
      "coverage": {...}
    }
  ]
}
```

## Data & Integrations

### External Systems

**LLM Providers:**
- OpenAI API (GPT-4, GPT-4 Turbo, GPT-4o-mini)
- Anthropic API (Claude-3.5-Sonnet)

**Caching:**
- Redis for JD signal caching (optional, falls back to no-op)

**NLP Processing:**
- spaCy for named entity recognition and text processing
- scikit-learn for TF-IDF analysis

### Data Flow

1. **Input**: Job description (URL or text) + resume bullets
2. **Processing**: Multi-stage pipeline with caching and validation
3. **Output**: Structured JSON with revised bullets, scores, coverage analysis, and validation flags

## Security & Permissions

### Input Validation
- Request size limiting (10MB max)
- Input sanitization against injection attacks
- Suspicious pattern detection and logging
- PII detection and flagging

### Rate Limiting
- Global rate limiting (5 requests/minute for processing)
- Custom rate limiting for health checks (100/minute)
- IP-based tracking and monitoring

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: geolocation=(), microphone=(), camera=()

### Cost Controls
- Daily cost limits with usage tracking
- Request count limits
- Model-specific cost estimation
- Automatic blocking when limits exceeded

### Security Monitoring
- Failed request tracking per IP
- Suspicious pattern detection
- High request rate detection
- Security statistics in health endpoint

## Limitations & Known Unknowns

### Current Limitations

**Dependencies:**
- spaCy model (`en_core_web_sm`) must be installed separately for local JD parsing
- Redis is optional but recommended for production caching

**Processing Constraints:**
- Maximum 20 bullets per request (configurable)
- Maximum 50KB job description text
- Maximum 1KB per individual bullet
- Maximum 50 candidates per bulk request

**LLM Dependencies:**
- Requires active internet connection for LLM API calls
- No offline processing capability
- Cost per request varies by model and input size

**Caching Limitations:**
- In-memory job storage (not persistent across restarts)
- Redis cache is optional and falls back to no-op
- No database persistence for job results

### Configuration Assumptions

**Environment Variables:**
- Assumes `.env` file loading in state machine CLI usage
- Default CORS origins set for localhost:3000 and localhost:3001 development
- Cost limits default to $100/day and 1000 requests/day

**Model Defaults:**
- OpenAI: `gpt-4-turbo-preview`
- Anthropic: `claude-3-5-sonnet-20241022`
- Temperature: 0.3 for consistency

**Security Defaults:**
- 10MB request size limit
- 5 requests/minute rate limit for processing
- 1-hour cache TTL for JD signals

### Potential Issues

**Error Handling:**
- Some LLM failures may result in fallback to original bullets
- Batch processing failures fall back to individual processing
- Redis connection failures are handled gracefully with no-op cache

**Performance:**
- No connection pooling for HTTP requests
- In-memory storage may not scale for high concurrent usage
- No request queuing or background job processing

**Validation:**
- Factual consistency checking relies on LLM interpretation
- Grammar checking requires external LanguageTool service
- PII detection uses regex patterns (may have false positives/negatives)

## Codebase Structure

```
ATS_Resume_Agent/
├── agents/                 # Core AI agent components
│   ├── fused_processor.py  # Batch rewrite + score processor
│   ├── jd_parser.py        # Job description parsing (hybrid local/LLM)
│   ├── rewriter.py         # Resume bullet rewriting
│   ├── scorer.py           # Bullet scoring (relevance, impact, clarity)
│   └── validator.py        # Validation (grammar, PII, consistency)
├── api/                    # Web API layer
│   └── main.py            # FastAPI application with endpoints
├── orchestrator/          # Workflow orchestration
│   └── state_machine.py   # 6-stage state machine
├── ops/                   # Operational infrastructure
│   ├── llm_client.py      # Unified LLM client (OpenAI/Anthropic)
│   ├── redis_cache.py     # Caching layer
│   ├── input_sanitizer.py # Security input validation
│   ├── cost_controller.py # Cost management
│   ├── security_monitor.py # Security monitoring
│   ├── logging.py         # Structured logging
│   ├── retry.py           # Retry logic with backoff
│   ├── ulid_gen.py        # ULID generation
│   └── simple_rate_limiter.py # Fallback rate limiting
├── schemas/               # Data models
│   └── models.py          # Pydantic models and validation
├── scripts/               # Utility scripts
│   ├── start_server.py    # Development server startup
│   └── benchmark_pipeline.py # Performance testing
├── tests/                 # Test suite
│   ├── integration/       # Integration tests
│   ├── api/              # API tests
│   └── security/         # Security tests
├── pyproject.toml        # Project configuration
├── requirements.txt      # Dependencies
├── Dockerfile           # Container configuration
└── render.yaml          # Deployment configuration
```

---

*All claims in this document are based strictly on code inspection and verified implementation details.*
