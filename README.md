# ATS Resume Engine - B2B Bulk Processing API

## Overview

**B2B Resume Rewrite Engine** for enterprise recruiters, staffing firms, and ATS/CRM integrations. Process multiple candidate resumes against a single job description with AI-powered rewriting, validation, and scoring.

**Core Value**: Make recruiters 3-5× faster in tailoring candidate resumes to job requirements without fabrication.

## Product Identity

- **Target Users**: Staffing firms, RPO providers, talent acquisition teams
- **Primary Workflow**: Bulk processing (one JD → many candidates)
- **Input Method**: Manual text only (no file uploads, no URL scraping)
- **Integration**: API-first, designed for ATS/CRM integration

## Key Features

### Bulk Processing API
- Process up to 50 candidates per batch against a single job description
- Background processing with job status tracking
- Structured results with coverage metrics and validation flags

### AI-Powered Rewriting
- 6-stage state machine pipeline for reliable processing
- Hybrid JD parsing (local NLP + LLM fallback)
- Fused processor (rewrite + score in single LLM call)
- Preserves factual accuracy - never fabricates tools or metrics

### Validation & Compliance
- PII detection (regex-based for emails, phones, SSN)
- Factual consistency checking (prevents invented skills/metrics)
- Input sanitization and rate limiting
- Configurable cost ceilings

### Coverage Metrics
- Relevance scoring (JD alignment)
- Impact scoring (outcomes and achievements)
- Clarity scoring (conciseness)
- Top terms coverage analysis

## API Endpoints

### Primary Endpoint: Bulk Processing

**POST** `/api/bulk/process`

Process multiple candidates against a single job description.

**Request:**
```json
{
  "job_description": "We are seeking a Senior Software Engineer...",
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "bullets": [
        "Built web applications using Python",
        "Led team of 5 developers"
      ]
    },
    {
      "candidate_id": "candidate_002",
      "bullets": [
        "Managed database operations",
        "Implemented CI/CD pipelines"
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

### Status Tracking

**GET** `/api/bulk/status/{job_id}`

Check processing status of a bulk job.

**GET** `/api/bulk/results/{job_id}`

Retrieve results when processing is complete.

### Testing Endpoint

**POST** `/api/resume/process`

Single resume processing endpoint for testing/development only. Accepts manual text input via form parameters:
- `resume_text`: Resume bullets (newline-separated)
- `role`: Target role
- `jd_text`: Job description text
- `extra_context`: Optional additional context

**Note**: For production use, please use `/api/bulk/process`.

## Architecture

### 6-Stage State Machine Pipeline

1. **INGEST**: Normalize inputs and compute JD hash
2. **EXTRACT_SIGNALS**: Parse JD using hybrid approach (spaCy + TF-IDF + LLM fallback)
3. **PROCESS**: Batch rewrite bullets using fused processor
4. **VALIDATE**: Check for PII, factual consistency
5. **OUTPUT**: Assemble results with coverage analysis
6. **COMPLETED**: Return final results

### Core Components

**Agents** (`agents/`)
- `jd_parser.py` - Job description signal extraction
- `fused_processor.py` - Batch rewrite + score processor
- `rewriter.py` - Individual bullet rewriter
- `scorer.py` - Coverage analysis and scoring
- `validator.py` - PII detection and factual consistency

**Orchestrator** (`orchestrator/`)
- `state_machine.py` - 6-stage processing pipeline

**Operations** (`ops/`)
- `llm_client.py` - Multi-provider LLM client (OpenAI, Anthropic)
- `redis_cache.py` - JD signal caching
- `cost_controller.py` - Daily cost and request limits
- `input_sanitizer.py` - Security sanitization
- `security_monitor.py` - Suspicious activity tracking
- `simple_rate_limiter.py` - Rate limiting

**API** (`api/`)
- `main.py` - FastAPI REST API with security middleware

**Schemas** (`schemas/`)
- `models.py` - Pydantic models for validation

## Installation

### Prerequisites
- Python 3.11+
- Redis (optional, for caching)
- OpenAI or Anthropic API key

### Setup

1. **Clone repository**
```bash
git clone <repository-url>
cd ATS_Resume_Agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```bash
# LLM Provider
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here

# Customer API Keys (format: customer_id:api_key,customer_id:api_key)
CUSTOMER_API_KEYS=pilot1:sk_live_abc123,pilot2:sk_live_xyz789

# Optional
REDIS_URL=redis://localhost:6379/0
MAX_DAILY_COST=100.0
MAX_REQUESTS_PER_DAY=1000
ALLOWED_ORIGINS=http://localhost:3000
```

4. **Run server**
```bash
uvicorn api.main:app --reload
```

Server runs at `http://localhost:8000`

## Usage Example

### Python Client

```python
import requests

# Set your API key
headers = {"X-API-Key": "sk_live_abc123"}

# Bulk processing
response = requests.post(
    "http://localhost:8000/api/bulk/process",
    headers=headers,
    json={
        "job_description": "Senior Software Engineer with Python experience...",
        "candidates": [
            {
                "candidate_id": "candidate_001",
                "bullets": [
                    "Built web applications using Python",
                    "Led team of 5 developers"
                ]
            }
        ],
        "settings": {
            "tone": "professional",
            "max_len": 30,
            "variants": 1
        }
    }
)

job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:8000/api/bulk/status/{job_id}", headers=headers)
print(status.json())

# Get results when complete
results = requests.get(f"http://localhost:8000/api/bulk/results/{job_id}", headers=headers)
print(results.json())
```

### cURL Example

```bash
curl -X POST http://localhost:8000/api/bulk/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_abc123" \
  -d '{
    "job_description": "Senior Software Engineer...",
    "candidates": [
      {
        "candidate_id": "candidate_001",
        "bullets": ["Built web applications", "Led team"]
      }
    ]
  }'
```

## Security Features

- **Input Sanitization**: All inputs validated and sanitized
- **Rate Limiting**: 5 requests/minute per IP for bulk processing
- **Cost Controls**: Daily cost and request limits
- **Security Monitoring**: Suspicious activity tracking
- **PII Detection**: Automatic flagging of personal information
- **CORS**: Configurable allowed origins

## Configuration

### Cost Controls

Set in environment variables:
```bash
MAX_DAILY_COST=100.0          # Maximum daily cost in USD
MAX_REQUESTS_PER_DAY=1000     # Maximum requests per day
```

### Processing Limits

- Maximum candidates per bulk request: 50
- Maximum bullets per candidate: 20
- Maximum bullet length: 1000 characters
- Maximum JD length: 50,000 characters

### LLM Settings

Configure via `JobSettings` in request:
```json
{
  "tone": "professional",  // or "concise", "technical"
  "max_len": 30,          // max words per bullet (1-100)
  "variants": 1           // number of variants (1-3)
}
```

## Limitations

- **In-memory storage**: Job results not persistent across restarts
- **No authentication**: Public API without user auth (add auth layer for production)
- **Single Redis instance**: No clustering or failover
- **Manual text input only**: No file uploads or resume parsing
- **No URL scraping**: Job descriptions must be provided as text

## Testing

Run test suite:
```bash
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/api/ -v              # API tests
pytest tests/integration/ -v      # Integration tests
pytest tests/security/ -v         # Security tests
```

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

For detailed API documentation, see [docs/API.md](docs/API.md)

## Support

For issues or questions:
1. Check [docs/](docs/) directory for detailed documentation
2. Review test examples in [tests/](tests/)
3. Open an issue on GitHub

## License

[Add your license here]


