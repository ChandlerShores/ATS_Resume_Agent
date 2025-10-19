# Architecture Documentation

## System Overview

The ATS Resume Agent is a production-ready, multi-agent AI system designed to optimize resume bullets for Applicant Tracking Systems (ATS). It uses a durable state machine architecture with specialized AI agents to process, rewrite, score, and validate resume content.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI REST API                         │
│                     (api/main.py)                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  POST /api/resume/process (async with background jobs)    │ │
│  │  POST /api/test/process-sync (synchronous)                │ │
│  │  GET  /health (monitoring)                                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    State Machine Orchestrator                   │
│                 (orchestrator/state_machine.py)                 │
│                                                                 │
│  INGEST → EXTRACT_SIGNALS → REWRITE → SCORE_SELECT → VALIDATE →OUTPUT  │
└─────────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
┌─────────────────────────────┐  ┌────────────────────────────┐
│      AI Agent System        │  │   Operational Services     │
│       (agents/)             │  │        (ops/)              │
├─────────────────────────────┤  ├────────────────────────────┤
│  • JD Parser                │  │  • LLM Client              │
│  • Rewriter                 │  │  • Logging                 │
│  • Scorer                   │  │  • Cost Controller         │
│  • Validator                │  │  • Security Monitor        │
└─────────────────────────────┘  │  • Input Sanitizer         │
                                 │  • Rate Limiter            │
                                 │  • Retry Logic             │
                                 │  • Hashing & ULID          │
                                 └────────────────────────────┘
                                              │
                                              ▼
                                 ┌────────────────────────────┐
                                 │   LLM Provider APIs        │
                                 │  (OpenAI / Anthropic)      │
                                 └────────────────────────────┘
```

---

## Core Components

### 1. API Layer (`api/main.py`)

**Purpose**: HTTP interface for client applications

**Key Features**:
- FastAPI framework with automatic OpenAPI documentation
- Async background job processing
- CORS middleware for frontend integration
- Rate limiting (SlowAPI)
- Security headers and request size limits
- Global exception handling

**Endpoints**:
- `POST /api/resume/process` - Async job submission (returns job_id)
- `GET /api/resume/status/{job_id}` - Check job status
- `GET /api/resume/result/{job_id}` - Retrieve results
- `POST /api/test/process-sync` - Synchronous processing (testing)
- `GET /health` - Health check with security stats

**Security Controls**:
- Input validation via Pydantic schemas
- Request body size limit (10MB)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- CORS with specific origin allowlist
- Error message sanitization

---

### 2. State Machine (`orchestrator/state_machine.py`)

**Purpose**: Orchestrates the 6-stage workflow with durability and idempotency

**Architecture Pattern**: Finite State Machine

**States**:

1. **INGEST**
   - Resolve job description (URL or text)
   - Normalize and validate inputs
   - Compute JD hash for idempotency
   - Categorize bullets

2. **EXTRACT_SIGNALS**
   - Parse JD with LLM
   - Extract top 25 keywords
   - Categorize: soft skills, hard tools, domain terms
   - Build synonym map

3. **REWRITE**
   - Generate bullet variants (default: 2 per bullet)
   - Apply anti-fabrication rules
   - Use role-appropriate terminology
   - Preserve factual accuracy

4. **SCORE_SELECT**
   - Score each variant (relevance, impact, clarity)
   - Compute JD term coverage
   - Return all variants with scores

5. **VALIDATE**
   - Check grammar and active voice
   - Detect PII (email, phone, SSN)
   - Verify factual consistency
   - Apply safe fixes (remove filler phrases)

6. **OUTPUT**
   - Assemble structured response
   - Include scoring, coverage, and red flags
   - Attach execution logs

**Error Handling**:
- Retries with exponential backoff on transient errors
- Comprehensive error logging with job_id correlation
- DLQ pattern for failed jobs (future)

**Idempotency**:
- Key: `sha256(job_id + jd_hash + bullets + settings)`
- Safe retries without duplicate processing
- Redis-based (planned) or in-memory caching

---

### 3. AI Agent System (`agents/`)

#### JD Parser Agent (`jd_parser.py`)

**Purpose**: Extract and categorize keywords from job descriptions

**Process**:
1. Fetch JD from URL (with retry logic) or use provided text
2. Normalize text (remove HTML, extra whitespace)
3. Call LLM to extract:
   - Top 25 priority terms
   - Weights (1.0 = must-have, 0.5 = nice-to-have)
   - Synonyms for flexible matching
   - Thematic groupings
4. Categorize keywords:
   - **Soft skills**: Transferable competencies (analytical thinking, communication)
   - **Hard tools**: Specific tools/platforms (Marketo, Salesforce, Python)
   - **Domain terms**: Industry terminology (B2B SaaS, healthcare, fintech)

**Anti-Hallucination**:
- Strict JSON schema enforcement
- Term count limits (max 25)
- Category validation

#### Rewriter Agent (`rewriter.py`)

**Purpose**: Transform resume bullets to be ATS-friendly and JD-aligned

**Core Philosophy**: Edit, don't invent

**Anti-Fabrication Rules**:
1. **Metrics Rule**: Only use metrics from the specific bullet being edited
2. **Tools Rule**: Never add tools/platforms not in original bullet
3. **Activity Rule**: Preserve core activity type (research stays research, not marketing)
4. **Context Rule**: Domain terms only if already present or clearly implied

**Process**:
1. Analyze original bullet for core activity and metrics
2. Identify demonstrated soft skills (e.g., "synthesized data" → analytical thinking)
3. Generate variants (default: 2) with:
   - Action verb first
   - JD-aligned soft skills
   - Original hard tools only
   - Impact-focused language
   - Oxford comma
   - ≤30 words
4. Return variants with rationale explaining changes

**Example**:
```
Original: "Built dashboards for stakeholders"
JD has: analytical thinking (soft skill), Tableau (hard tool)

Correct:
"Applied analytical thinking to build dashboards, synthesizing data for executive stakeholders"
(Added soft skill, kept activity, didn't fabricate Tableau)

Incorrect:
"Built Tableau dashboards, increasing revenue 30%"
(Fabricated tool and metric)
```

#### Scorer Agent (`scorer.py`)

**Purpose**: Evaluate bullet variants on three dimensions

**Scoring Criteria**:
1. **Relevance (0-100)**: JD alignment
   - 90-100: Multiple must-have skills matched
   - 70-89: Some important terms matched
   - 50-69: Tangentially related
   - <50: Poor alignment

2. **Impact (0-100)**: Outcomes and achievements
   - 90-100: Quantified outcome with business impact
   - 70-89: Qualitative impact with scope/scale
   - 50-69: Action described but outcome unclear
   - <50: No clear value

3. **Clarity (0-100)**: Brevity and concreteness
   - 90-100: Crisp, concrete, no filler
   - 70-89: Clear but could be tighter
   - 50-69: Somewhat vague or wordy
   - <50: Confusing or grammatically poor

**Coverage Analysis**:
- Hit terms: JD keywords present in revised bullets
- Miss terms: JD keywords missing from bullets
- Considers synonyms for flexible matching

#### Validator Agent (`validator.py`)

**Purpose**: Quality assurance and factual consistency checks

**Validation Checks**:
1. **Regex-based**:
   - PII detection (email, phone, SSN)
   - Filler phrases ("responsible for", "duties included")
   - Passive voice indicators ("was responsible", "were assigned")

2. **LLM-based**:
   - Grammar and punctuation
   - Factual consistency with original
   - Hard tool fabrication detection
   - Borrowed metrics detection
   - Activity mismatch detection

**Safe Fixes**:
- Remove filler phrases
- Fix grammar/punctuation
- Capitalize first letter
- Clean extra whitespace

**Red Flags**:
- PII detected
- Passive phrasing
- Vague outcomes
- Unsupported claims
- Hard tool fabrication
- Borrowed metrics

---

### 4. Operational Services (`ops/`)

#### LLM Client (`llm_client.py`)

**Purpose**: Unified interface for multiple LLM providers

**Supported Providers**:
- OpenAI (GPT-4o-mini, GPT-4-turbo, GPT-4)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)

**Features**:
- Provider abstraction (consistent API)
- JSON response parsing
- Temperature and token control
- Error handling

**Configuration**:
```python
client = LLMClient(
    provider="openai",  # or "anthropic"
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=2000
)
```

#### Logging (`logging.py`)

**Purpose**: Structured logging with job correlation

**Format**: JSON with consistent schema
```json
{
  "ts": "2025-10-11T19:00:00.000Z",
  "level": "info",
  "stage": "REWRITE",
  "msg": "Generated 6 variants",
  "job_id": "01HX...",
  "count": 6
}
```

**Levels**: INFO, WARN, ERROR

**Benefits**:
- Easy parsing and filtering
- Job tracing via job_id
- Stage-based filtering
- Timestamp for debugging

#### Cost Controller (`cost_controller.py`)

**Purpose**: Prevent LLM API cost overruns

**Features**:
- Daily cost limit (default $100)
- Daily request limit (default 1000)
- Per-model cost estimation
- Pre-request validation (blocks before LLM call)
- Real-time tracking
- Warnings at 80% of limits

**Cost Estimates**:
- gpt-4o-mini: ~$0.01/request
- gpt-4-turbo: ~$0.05/request
- claude-3-5-sonnet: ~$0.03/request

#### Security Monitor (`security_monitor.py`)

**Purpose**: Track suspicious activity and security events

**Monitored Events**:
- Failed requests per IP (max 10/hour)
- Suspicious input patterns
- High request rates (20/min threshold)
- Security anomalies

**Features**:
- Per-IP tracking with automatic cleanup
- Real-time alerts
- Stats available via `/health` endpoint

#### Input Sanitizer (`input_sanitizer.py`)

**Purpose**: Detect and neutralize malicious input

**Dangerous Patterns** (18+):
- Prompt injection: "ignore all previous instructions"
- SQL injection: "'; DROP TABLE"
- XSS: `<script>`, `<iframe>`
- Path traversal: "../", "file://"
- Command injection: "|", "&&", ";"

**Actions**:
- Pattern replacement with `[FILTERED]`
- HTML escaping
- Length truncation
- Suspicious pattern logging

#### Rate Limiter (`simple_rate_limiter.py`)

**Purpose**: Prevent API abuse

**Implementation**: In-memory token bucket (scalable to Redis)

**Limits**:
- 5 requests/minute on expensive operations
- 100 requests/minute on health checks
- Per-IP tracking

**Integration**: SlowAPI middleware + custom decorator

---

### 5. Data Models (`schemas/models.py`)

**Purpose**: Type-safe data structures with validation

**Key Models**:
- `JobInput`: Request schema with field validation
- `JobOutput`: Response schema with structured results
- `JobState`: Internal state passed between workflow stages
- `JDSignals`: Extracted keywords with categorization
- `BulletResult`: Scored variants with diffs
- `ValidationResult`: Quality check results

**Validation Features**:
- Field length limits (security)
- Type enforcement
- Required field checking
- Custom validators (e.g., bullet length)

**Example**:
```python
class JobInput(BaseModel):
    role: str = Field(..., max_length=200)
    jd_text: str | None = Field(None, max_length=50000)
    bullets: list[str] = Field(..., min_length=1, max_length=20)
    
    @field_validator("bullets")
    @classmethod
    def validate_bullets(cls, v):
        return [b[:1000] for b in v if b.strip()]
```

---

## Data Flow

### Request Lifecycle

1. **Client Request**
   ```
   POST /api/test/process-sync
   {
     "role": "Software Engineer",
     "jd_text": "...",
     "bullets": ["...", "..."]
   }
   ```

2. **API Layer** (`api/main.py`)
   - Rate limit check (5/min)
   - Cost limit check
   - Input sanitization
   - Pydantic validation
   - Create job_id (ULID)

3. **State Machine** (`orchestrator/state_machine.py`)
   - INGEST: Normalize inputs, compute jd_hash
   - EXTRACT_SIGNALS: LLM call to parse JD
   - REWRITE: LLM call per bullet (2 variants)
   - SCORE_SELECT: LLM call to score variants
   - VALIDATE: LLM call for consistency check
   - OUTPUT: Assemble response

4. **Response**
   ```json
   {
     "job_id": "01HX...",
     "summary": { ... },
     "results": [
       {
         "original": "...",
         "revised": ["...", "..."],
         "scores": { "relevance": 92, "impact": 85, "clarity": 95 }
       }
     ]
   }
   ```

**LLM API Calls Per Request**:
- JD Parser: 1 call
- Rewriter: N calls (N = number of bullets)
- Scorer: N calls (one per bullet)
- Validator: N calls (one per bullet)

**Total**: 1 + 3N calls (e.g., 3 bullets = 10 calls)

---

## Scalability Considerations

### Current Architecture (Single Instance)
- In-memory job storage (lost on restart)
- In-memory rate limiting (per-instance)
- No horizontal scaling

### Scaling Strategy (Future)

1. **Job Storage**
   - Move to Redis or PostgreSQL
   - Persistent job results
   - Distributed access

2. **Rate Limiting**
   - Redis-backed rate limiter
   - Shared across instances
   - API gateway integration

3. **Background Processing**
   - Celery + Redis queue
   - Worker pool for LLM calls
   - Retry and DLQ handling

4. **Caching**
   - Redis cache for JD parsing results
   - Cache key: jd_hash
   - TTL: 1 hour

5. **Load Balancing**
   - Multiple API instances behind load balancer
   - Health check-based routing
   - Session affinity (if needed)

---

## Security Architecture

### Defense in Depth

**Layer 1: Network**
- HTTPS only (TLS 1.2+)
- CORS with specific origins
- Rate limiting at edge (future: Cloudflare)

**Layer 2: API Gateway**
- Request size limits (10MB)
- Rate limiting (SlowAPI)
- Security headers
- IP-based tracking

**Layer 3: Application**
- Input sanitization (18+ patterns)
- Pydantic validation
- SQL injection prevention (no database)
- XSS prevention (HTML escaping)

**Layer 4: Business Logic**
- Cost controls (daily limits)
- Anti-fabrication rules
- PII detection
- LLM-based validation

**Layer 5: Monitoring**
- Security monitor (suspicious IPs)
- Structured logging
- Failed request tracking
- Real-time alerts

---

## Deployment Architecture

### Container Architecture (Docker)

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
# Non-root user
RUN useradd --uid 1000 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY . /app
USER appuser
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Benefits**:
- Minimal attack surface
- Non-root execution
- Cached dependencies
- Production-ready

### Cloud Deployment (Render.com)

```yaml
# render.yaml
services:
  - type: web
    name: ats-resume-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
```

**Features**:
- Auto-deploy from GitHub
- Free tier available
- Automatic HTTPS
- Health checks

---

## Performance Characteristics

### Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| Health check | <50ms | No LLM calls |
| JD parsing | 3-8s | 1 LLM call |
| Bullet rewrite | 5-10s/bullet | 3 LLM calls per bullet |
| Complete request | 30-90s | Depends on bullet count |
| Cold start | +30s | Free tier only |

### Throughput

- **Rate limit**: 5 requests/minute (configurable)
- **Concurrent**: 1-2 requests (single instance)
- **Daily**: 1000 requests max (cost control)

### Resource Usage

- **Memory**: ~100-200MB per request
- **CPU**: Minimal (I/O bound, waiting on LLM)
- **Network**: 50-100KB request, 100-500KB response

---

## Monitoring & Observability

### Metrics

- Active jobs count
- Request rate (per minute, per day)
- LLM cost (per day)
- Error rate (by type)
- Suspicious IP count

### Logs

All logs are JSON structured:
```json
{
  "ts": "2025-10-11T19:00:00.000Z",
  "level": "info",
  "stage": "REWRITE",
  "msg": "Rewritten 3 bullets",
  "job_id": "01HX...",
  "count": 3
}
```

**Log Levels**:
- INFO: Normal operation
- WARN: Security events, approaching limits
- ERROR: Failures, exceptions

### Health Endpoint

`GET /health` returns:
```json
{
  "status": "healthy",
  "active_jobs": 0,
  "cost_warnings": [],
  "security": {
    "suspicious_ips": 0,
    "total_failed_attempts": 0
  }
}
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API** | FastAPI + Uvicorn | HTTP server |
| **LLM** | OpenAI / Anthropic | AI processing |
| **Validation** | Pydantic v2 | Schema validation |
| **ID Generation** | ULID | Sortable unique IDs |
| **Retry** | Tenacity | Exponential backoff |
| **Rate Limiting** | SlowAPI | Request throttling |
| **Containerization** | Docker | Deployment packaging |
| **Hosting** | Render.com | Cloud platform |

---

## Future Architecture Enhancements

1. **Async LLM Calls**: Parallel processing of multiple bullets
2. **Redis Integration**: Job storage, rate limiting, caching
3. **Database**: Persistent job history and analytics
4. **Webhook Callbacks**: Notify clients when jobs complete
5. **API Authentication**: JWT or API key-based auth
6. **GraphQL API**: Flexible querying (alternative to REST)
7. **Streaming Responses**: Real-time progress updates
8. **Multi-tenancy**: Isolated environments per customer

---

## Contributing to Architecture

When proposing architectural changes:
1. Consider backward compatibility
2. Document performance implications
3. Update this document
4. Add tests for new components
5. Consider security implications
6. Plan for scalability

