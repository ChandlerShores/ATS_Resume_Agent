# ATS Resume Bullet Revisor

> A durable multi-agent system that rewrites resume bullets to be ATS-friendly, impact-focused, and tightly aligned to job descriptions.

## Overview

This system takes raw resume bullets and transforms them into concise (≤30 words), JD-aligned, impact-forward variants. It returns structured JSON with scores, coverage analysis, red flags, and detailed rationale for each change.

**Key Features:**
- 🎯 **JD Alignment**: Extracts key terms from job descriptions and aligns bullets accordingly
- 📊 **Impact Scoring**: Evaluates relevance, impact, and clarity (0-100 scale)
- ✅ **Validation**: Checks for PII, filler phrases, passive voice, and grammar issues
- 🔄 **Idempotency**: Same input always produces same output
- 🛡️ **Durability**: Retries with exponential backoff, DLQ for failures
- 📝 **Observability**: Structured logging with job_id correlation

## Quick Start

### Installation

1. **Clone the repository**
```bash
git clone <repo-url>
cd ATS_Resume_Agent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp env.example .env
# Edit .env and add your API keys
```

Required environment variables:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (depending on provider)
- `LLM_PROVIDER` (either "openai" or "anthropic")

### Usage

**Run with sample data:**
```bash
python -m orchestrator.state_machine --input tests/sample_input.json --out out/result.json
```

**Run with custom input:**
```bash
python -m orchestrator.state_machine --input your_input.json --out your_output.json
```

## Input Format

```json
{
  "role": "Senior Financial Analyst",
  "jd_text": "Full job description text...",
  "jd_url": "https://example.com/job (optional)",
  "bullets": [
    "Original resume bullet 1",
    "Original resume bullet 2"
  ],
  "metrics": {
    "key": "value"
  },
  "extra_context": "Additional context (optional)",
  "settings": {
    "tone": "concise",
    "max_len": 30,
    "variants": 2
  },
  "job_id": "01HX5PQRS7891234567890ABCD (optional - auto-generated)"
}
```

## Output Format

```json
{
  "job_id": "01HX5PQRS7891234567890ABCD",
  "summary": {
    "role": "Senior Financial Analyst",
    "top_terms": ["financial modeling", "Power BI", "variance analysis", ...],
    "coverage": {
      "hit": ["Power BI", "variance analysis", ...],
      "miss": ["SQL", "Python", ...]
    }
  },
  "results": [
    {
      "original": "Responsible for creating monthly reports...",
      "revised": [
        "Built Power BI dashboards for financial KPIs, automating 15 reports and serving 45 users.",
        "Developed automated financial reporting in Power BI, reducing manual work and improving visibility."
      ],
      "scores": {
        "relevance": 92,
        "impact": 88,
        "clarity": 95
      },
      "notes": "Replaced passive phrasing with action verb, added JD-aligned terms (Power BI), included quantifiable metrics.",
      "diff": {
        "removed": ["responsible for"],
        "added_terms": ["Power BI", "automated", "dashboards"]
      }
    }
  ],
  "red_flags": [
    "Filler phrase: 'responsible for'",
    "Passive phrasing: 'was tasked'"
  ],
  "logs": [
    {
      "ts": "2024-03-15T10:30:45Z",
      "level": "info",
      "stage": "INGEST",
      "msg": "Ingested 5 bullets",
      "job_id": "01HX5PQRS7891234567890ABCD"
    }
  ]
}
```

## Architecture

### State Machine Flow

```
INGEST → EXTRACT_SIGNALS → REWRITE → SCORE_SELECT → VALIDATE → OUTPUT
```

1. **INGEST**: Fetch/normalize JD, compute hashes, check idempotency
2. **EXTRACT_SIGNALS**: Extract top 25 JD terms with weights and synonyms
3. **REWRITE**: Generate 2 variants per bullet using LLM
4. **SCORE_SELECT**: Score on relevance, impact, clarity
5. **VALIDATE**: Check grammar, active voice, PII, unsupported claims
6. **OUTPUT**: Assemble final JSON with coverage and logs

### Agents

- **JD_PARSER**: Analyzes job descriptions, extracts key competencies
- **REWRITER**: Generates ATS-friendly bullet variants
- **SCORER**: Evaluates bullets on multiple dimensions
- **VALIDATOR**: Enforces quality standards and safety checks

### Directory Structure

```
ATS_Resume_Agent/
├── orchestrator/
│   ├── state_machine.py      # Core workflow orchestrator
│   └── idempotency.py         # Idempotency management
├── agents/
│   ├── jd_parser.py           # JD analysis agent
│   ├── rewriter.py            # Bullet rewriting agent
│   ├── scorer.py              # Scoring agent
│   └── validator.py           # Validation agent
├── ops/
│   ├── logging.py             # Structured logging
│   ├── ulid_gen.py            # ULID generation
│   ├── hashing.py             # SHA256 utilities
│   ├── retry.py               # Retry with backoff
│   ├── dlq.py                 # Dead letter queue
│   ├── rate_limiter.py        # Rate limiting
│   └── llm_client.py          # Unified LLM client
├── schemas/
│   └── models.py              # Pydantic data models
├── tests/
│   └── sample_input.json      # Example input
├── out/                       # Output directory
└── requirements.txt
```

## Configuration

Edit `.env` to customize:

```bash
# LLM Provider
LLM_PROVIDER=openai           # or anthropic
LLM_MODEL=gpt-4-turbo-preview # or claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# Retry Configuration
MAX_RETRIES=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=30.0

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10

# Redis (optional)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
```

## Design Principles

### Hard Rules
- ❌ **Never invent** achievements, titles, companies, or numbers
- ✅ **Use provided metrics** exactly as given
- ✅ **Prefer strong verbs** and concrete nouns
- ✅ **Remove PII** (emails, phones, SSNs)
- ✅ **One idea per bullet**

### Style Guide
- **Concise**: ≤30 words
- **Action-first**: Start with strong verb
- **Impact-forward**: Show outcomes, not just tasks
- **Oxford comma**: For lists
- **Active voice**: No "responsible for" or passive constructions

## Durability Features

### Idempotency
Same input produces same output via SHA256 hashing:
```
key = sha256(job_id + jd_hash + bullets + settings)
```

### Retries
Exponential backoff with jitter on:
- JD URL fetching
- LLM API calls
- External service calls

### Dead Letter Queue (DLQ)
Failed jobs written to `out/dlq.jsonl` for replay:
```json
{"job_id": "...", "stage": "REWRITE", "reason": "...", "timestamp": "..."}
```

## Observability

### Structured Logs
All logs follow this format:
```json
{"ts": "2024-03-15T10:30:45Z", "level": "info", "stage": "INGEST", "msg": "...", "job_id": "..."}
```

### Metrics
- `rewritten_bullets_total`: Total bullets processed
- `validation_failures_total`: Validation issues found

### Tracing
All operations correlated by `job_id` (ULID).

## Development

### Run Tests
```bash
pytest tests/
```

### Format Code
```bash
black .
ruff check .
```

### Add New Agent
1. Create `agents/your_agent.py`
2. Define prompts and logic
3. Integrate into `orchestrator/state_machine.py`

## Troubleshooting

**Issue**: `OPENAI_API_KEY not set`
- **Solution**: Copy `env.example` to `.env` and add your API key

**Issue**: Job fails with "Rate limited"
- **Solution**: Adjust `RATE_LIMIT_REQUESTS_PER_MINUTE` in `.env`

**Issue**: LLM returns non-JSON
- **Solution**: Check `ops/llm_client.py` JSON parsing logic

**Issue**: Empty output
- **Solution**: Check `out/dlq.jsonl` for failure details

## Roadmap

- [ ] API layer (FastAPI)
- [ ] Redis-based idempotency cache
- [ ] Async/concurrent bullet processing
- [ ] Batch LLM calls for efficiency
- [ ] Prometheus metrics export
- [ ] Web UI for DLQ replay

## License

MIT

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

Built with ❤️ for job seekers everywhere.

