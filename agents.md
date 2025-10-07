Launchworthy ATS Resume Bullet Revisor — agents.md

> A small, durable multi‑agent system that rewrites resume bullets to be ATS‑friendly, impact‑focused, and tightly aligned to a job description (JD), with idempotency, retries, and simple observability baked in.




---

1) Overview

Goal: Convert raw resume bullets into concise (≤30 words), JD‑aligned, impact‑forward variants; return JSON with scores, coverage, red flags, and a brief rationale.

Style: Concise, direct, helpful; confident without overreach; Oxford comma. No invented facts or numbers.

Durability: Workflow runs as a state machine with idempotency keys, safe retries, and a single job_id across logs.



---

2) Inputs & Outputs

Input

{
  "role": "string",
  "jd_text": "string (or use jd_url)",
  "jd_url": "string (optional)",
  "bullets": ["..."],
  "metrics": { "k": "v" },
  "extra_context": "string (optional)",
  "settings": {"tone": "concise", "max_len": 30, "variants": 2},
  "job_id": "ULID | optional (auto‑create if missing)"
}

Output

{
  "job_id": "...",
  "summary": {
    "role": "...",
    "top_terms": ["..."],
    "coverage": {"hit": ["..."], "miss": ["..."]}
  },
  "results": [
    {
      "original": "...",
      "revised": ["...", "..."],
      "scores": {"relevance": 0, "impact": 0, "clarity": 0},
      "notes": "1–2 sentences explaining the changes.",
      "diff": {"removed": ["..."], "added_terms": ["..."]}
    }
  ],
  "red_flags": ["PII detected", "confidential detail", "unverified claim", "passive phrasing", "vague outcome"],
  "logs": [{"ts": "ISO", "level": "info|warn|error", "stage": "...", "msg": "...", "job_id": "..."}]
}


---

3) State Machine (Durable Workflow)

1. INGEST

Resolve jd_url if present; normalize text (trim, lowercase/lemmatize for matching).

Compute jd_hash = sha256(normalized_jd); normalize bullets; drop empties.

Log: info/ingested.



2. EXTRACT_SIGNALS

Pull competencies/skills from JD; prioritize must‑have > nice‑to‑have; build top_terms (≤25) and a synonyms map.

Log: info/extracted_signals.



3. REWRITE

For each bullet: produce 2 variants, ≤30 words, strong verb first, JD‑aligned terms, impact‑forward, Oxford comma.

If metrics provided, include them exactly; otherwise, keep qualitative. Never invent facts.

Log: info/rewritten with count.



4. SCORE_SELECT

Score each variant: Relevance (JD priority match), Impact (outcome/scope/efficiency), Clarity (brevity/concreteness).

Compose coverage report (hit/miss across top_terms). Return both variants.

Log: info/scored.



5. VALIDATE

Enforce grammar, active voice, no filler (e.g., “responsible for”).

Guardrail: do not introduce facts beyond input/metrics/context. Flag red flags; auto‑fix where safe.

Log: info/validated.



6. OUTPUT

Assemble JSON + readable summary; attach job_id everywhere.

Log: info/completed.





---

4) Idempotency, Retries, and DLQ

Idempotency key: sha256(job_id + jd_hash + join(bullets) + stringify(settings)).

Retries: Exponential backoff + jitter on external fetches (e.g., jd_url), max 3 attempts.

DLQ/Replay: On permanent failure, store {job_id, stage, reason}; provide a simple replay UI.



---

5) Observability & Rate Limits

Logs: {ts, level, stage, msg, job_id}.

Metrics: rewritten_bullets_total, validation_failures_total.

Tracing: Correlate by job_id.

Rate‑limit: Redis token bucket with jitter to avoid thundering herd when fan‑out.



---

6) Agents & Prompts

JD_PARSER

Responsibility: Extract prioritized terms/competencies and synonyms. Prompt:

> Extract up to 25 prioritized JD competencies/keywords. Group by theme, include synonyms. Output JSON: {top_terms, weights, synonyms}.



REWRITER

Responsibility: Rewrite each bullet into 2 ATS‑friendly variants. Prompt:

> Rewrite to ≤30 words, action verb first, JD‑aligned terms, impact‑forward, Oxford comma. Do not invent facts. If metrics provided, include them exactly; else keep qualitative. Return 2 variants + a 1‑sentence rationale.



SCORER

Responsibility: Score variants and explain briefly. Prompt:

> Score relevance (JD priority match), impact (outcome/scope/efficiency), clarity (brevity/concreteness). Return {relevance, impact, clarity} 0–100 + 1‑sentence why.



VALIDATOR

Responsibility: Guardrail checks and safe fixes. Prompt:

> Enforce active voice, remove filler, flag PII/confidential/unsupported claims. Ensure no new facts. Return {ok: bool, flags: [...], fixes: [...]}; apply safe fixes.




---

7) Policies (Hard Rules)

No invented achievements, titles, companies, or numbers.

Prefer strong verbs; concrete nouns; single idea per bullet.

Remove PII and confidential/client‑protected info.

If unverifiable claims appear, revise or drop; still report in red_flags.



---

8) Examples (Style Only; do not fabricate metrics)

“Automated month‑end close in D365, cutting cycle time 31%, standardizing templates across 12 entities, and improving variance visibility in Power BI.”

“Built Power BI cash‑flow views tied to GL, reducing manual reconciliation, and accelerating forecast reviews with controllership.”



---

9) Minimal API Surface (optional)

POST /revise → revised bullets + scores

POST /score → scores existing bullets

GET /glossary → verb bank & common metrics hints



---

10) Repo Scaffold

/orchestrator/state_machine.py   # states, retries, idempotency
/agents/jd_parser.py             # JD_PARSER agent
/agents/rewriter.py              # REWRITER agent
/agents/scorer.py                # SCORER agent
/agents/validator.py             # VALIDATOR agent
/schemas/io.json                 # I/O contracts
/tests/sample_input.json         # quick run example
/ops/logging.py                  # structured logs
/README.md                       # how to run & examples


---

11) Runbook (local CLI)

python -m orchestrator.state_machine \
  --input ./tests/sample_input.json \
  --out ./out/result.json

On success: print human summary (role, coverage hit/miss, top red_flags) and write JSON to ./out/result.json.

On failure: write DLQ entry {job_id, stage, reason} and exit non‑zero.