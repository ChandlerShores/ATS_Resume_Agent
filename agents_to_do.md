# Agent To-Do

Looking at this specification, here’s a high-level **implementation roadmap**:

---

## **Phase 1: Foundation & Infrastructure** (Days 1–2)

### 1. Project Setup
- [x] Initialize Python project structure with virtual environment.
- [x] Set up `pyproject.toml` or `requirements.txt` with dependencies:
  - LLM client (OpenAI/Anthropic SDK)
  - ULID generation library
  - HTTP client (for `jd_url` fetching)
  - NLP libraries (spaCy/NLTK for normalization/lemmatization)
  - Redis client (for rate limiting)
  - Pydantic (for schema validation)
- [x] Create directory structure as specified in section 10.
- [x] Initialize git repo, `.gitignore`, basic `.env` setup.

### 2. Core Utilities
- [x] `/ops/logging.py`: Structured logger with `{ts, level, stage, msg, job_id}` format.
- [x] `/ops/ulid_gen.py`: ULID generation for `job_id`.
- [x] `/ops/hashing.py`: SHA256 helpers for `jd_hash` and idempotency keys.
- [x] `/ops/rate_limiter.py`: Redis token bucket with jitter (or in-memory fallback for local dev).

---

## **Phase 2: Schemas & Contracts** (Day 3)

### 3. Data Models
- [x] `/schemas/io.json`: JSON schema for input/output contracts.
- [x] `/schemas/models.py`: Pydantic models for:
  - `JobInput` (role, jd_text, jd_url, bullets, metrics, settings, job_id)
  - `JobOutput` (job_id, summary, results, red_flags, logs)
  - `BulletResult` (original, revised, scores, notes, diff)
  - `Summary` (role, top_terms, coverage)
  - Internal state models for each stage.

---

## **Phase 3: Individual Agents** (Days 4–7)

### 4. JD_PARSER Agent
- [x] `/agents/jd_parser.py`:
  - Fetch `jd_url` if provided (with retry logic).
  - Normalize JD text (trim, lowercase, lemmatize).
  - LLM call to extract top 25 prioritized terms/competencies.
  - Build synonyms map.
  - Return `{top_terms, weights, synonyms}`.

### 5. REWRITER Agent
- [x] `/agents/rewriter.py`:
  - LLM prompt to generate 2 variants per bullet.
  - Enforce ≤30 words, action verb first, JD-aligned terms.
  - Include metrics if provided; never invent.
  - Return variants + rationale.

### 6. SCORER Agent
- [x] `/agents/scorer.py`:
  - Score each variant on relevance, impact, clarity (0–100).
  - Build coverage report (hit/miss terms).
  - Return scores + brief explanation.

### 7. VALIDATOR Agent
- [x] `/agents/validator.py`:
  - Check for active voice, remove filler words.
  - Flag PII patterns (emails, phones, SSNs).
  - Flag confidential/unverified claims.
  - Return `{ok, flags, fixes}` and apply safe fixes.

---

## **Phase 4: State Machine & Orchestration** (Days 8–10)

### 8. State Machine Core
- [x] `/orchestrator/state_machine.py`:
  - Define 6 states: INGEST → EXTRACT_SIGNALS → REWRITE → SCORE_SELECT → VALIDATE → OUTPUT.
  - State transition logic with logging at each step.
  - Thread `job_id` through all stages.
  - Accumulate logs in-memory, append to final output.

### 9. INGEST State
- [x] Resolve `jd_url` or use `jd_text`.
- [x] Compute `jd_hash`.
- [x] Normalize bullets, drop empties.
- [x] Generate `job_id` if missing.

### 10. Orchestration Glue
- [x] Wire agents into state machine.
- [x] Pass intermediate state between stages.
- [x] Handle errors gracefully at each stage.

---

## **Phase 5: Durability Features** (Days 11–12)

### 11. Idempotency
- [x] `/orchestrator/idempotency.py`:
  - Compute idempotency key: `sha256(job_id + jd_hash + bullets + settings)`.
  - Cache results (in-memory or Redis).
  - Return cached result if key matches.

### 12. Retries & DLQ
- [x] `/ops/retry.py`: Exponential backoff with jitter for external calls.
- [x] `/ops/dlq.py`: Store `{job_id, stage, reason}` on permanent failure.
- [x] Optional: Simple replay mechanism to reprocess DLQ entries.

---

## **Phase 6: Testing & Validation** (Days 13–14)

### 13. Test Data
- [x] `/tests/sample_input.json`: Realistic test case with JD and bullets.
- [ ] `/tests/fixtures/`: Additional test JDs and bullet sets.
- [ ] Edge cases: empty bullets, missing metrics, malformed JD.

### 14. Unit Tests
- [ ] Test each agent independently with mocked LLM responses.
- [ ] Test hashing, ULID generation, normalization.
- [ ] Test validator's PII detection.

### 15. Integration Tests
- [ ] End-to-end run through state machine.
- [ ] Verify idempotency (same input → same output).
- [ ] Test retry logic with simulated failures.
- [ ] Verify DLQ writes on permanent errors.

---

## **Phase 7: CLI & Documentation** (Day 15)

### 16. CLI Entry Point
- [x] `/orchestrator/cli.py` or enhance `state_machine.py`:
  - Parse `--input` and `--out` arguments.
  - Run state machine.
  - Print human-readable summary (role, coverage, red flags).
  - Write JSON to output file.
  - Exit codes: 0 on success, non-zero on failure.

### 17. Documentation
- [x] `README.md`:
  - Quick start guide.
  - Installation instructions.
  - Usage examples.
  - Sample input/output.
  - Architecture overview.
- [x] Inline code comments and docstrings.

---

## **Phase 8: Observability & Ops** (Optional, Days 16–17)

### 18. Metrics Collection
- [ ] Instrument counters: `rewritten_bullets_total`, `validation_failures_total`.
- [ ] Export to Prometheus or simple JSON log.

### 19. Tracing
- [ ] Add trace IDs (already using `job_id`).
- [ ] Optional: OpenTelemetry integration.

---

## **Phase 9: API Layer** (Optional, Days 18–20)

### 20. REST API
- [ ] `/api/server.py`: FastAPI or Flask.
  - `POST /revise`: Run full pipeline.
  - `POST /score`: Score existing bullets.
  - `GET /glossary`: Return verb bank & metrics hints.
- [ ] API documentation (Swagger/OpenAPI).

### 21. Verb Bank / Glossary
- [ ] `/data/verb_bank.json`: Curated list of strong action verbs.
- [ ] `/data/metrics_hints.json`: Common metrics patterns.

---

## **Phase 10: Polish & Production Readiness** (Optional, Days 21+)

### 22. Configuration Management
- [ ] Externalize settings (LLM model, temperature, max retries, rate limits).
- [ ] Environment-based configs (dev/prod).

### 23. Error Handling Refinement
- [ ] Friendly error messages.
- [ ] Validation of input JSON schema.

### 24. Performance Optimization
- [ ] Batch LLM calls where possible.
- [ ] Async/concurrent processing for multiple bullets.
- [ ] Caching LLM responses for identical inputs.

### 25. Security
- [ ] Sanitize `jd_url` to prevent SSRF.
- [ ] Rate limiting on API endpoints.
- [ ] Redact PII from logs.

---

## **Critical Path Priorities**

**MVP (Minimum Viable Product):**
1. ✅ Phases 1–4: Foundation, schemas, agents, basic state machine. **COMPLETED**
2. ✅ Phase 6 (partial): At least one sample test. **COMPLETED**
3. ✅ Phase 7: CLI to run locally. **COMPLETED**

**Launch-Ready:**
- ✅ Add Phase 5 (durability). **COMPLETED**
- Phase 6 (full testing). **IN PROGRESS**
- ✅ Phase 7 documentation. **COMPLETED**

**Production-Grade:**
- Phases 8–10 (observability, API, polish). **PENDING**

---

## **Key Decision Points**

1. **LLM Provider**: OpenAI (GPT-4) vs Anthropic (Claude) vs local/open-source?
2. **State Persistence**: In-memory only for MVP, or Redis/DB from the start?
3. **Rate Limiting**: Redis required or mock for local dev?
4. **API Priority**: Build API early or focus on CLI first?
