from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Load .env file if it exists (for local development)
load_dotenv()

from .config import ATTACHED_VERSIONS, OPENAI_MODEL
from .logging_utils import get_logger, log_json
from .metrics import compute_input_metrics
from .normalizer import normalize_text, normalize_resume_bullets, truncate_jd_to_core_sections
from .prompt_assembler import assemble_messages
from .rate_limiter import rate_limit_dependency
from .schemas import ParamsModel, RewriteRequest, RewriteResponse
from .validator import validate_and_reconcile
from .clients.openai_client import call_model_with_repair


app = FastAPI(title="ATS Resume Rewriter API", version=ATTACHED_VERSIONS["api_version"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_logger = get_logger("ats_resume_api")
_start_time = datetime.now(timezone.utc)


@app.get("/health")
def health() -> Dict[str, Any]:
    uptime_seconds = int((datetime.now(timezone.utc) - _start_time).total_seconds())
    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
        "model": OPENAI_MODEL,
        **ATTACHED_VERSIONS,
    }


@app.get("/version")
def version() -> Dict[str, str]:
    return ATTACHED_VERSIONS


@app.post("/api/rewrite", response_model=RewriteResponse)
def rewrite_endpoint(payload: RewriteRequest, _: None = Depends(rate_limit_dependency)) -> Any:
    # Prepare request_id
    if not payload.params.request_id:
        payload.params = ParamsModel(**{**payload.params.model_dump(), "request_id": str(uuid.uuid4())})
    request_id = payload.params.request_id

    # Normalize inputs
    jd_raw = payload.job_description
    bullets_raw = payload.resume_bullets
    jd_norm = normalize_text(jd_raw)
    jd_core = truncate_jd_to_core_sections(jd_norm)
    bullets_norm = normalize_resume_bullets(bullets_raw)

    # Build final request object for prompting
    norm_payload = RewriteRequest(job_description=jd_core, resume_bullets=bullets_norm, params=payload.params)

    # Assemble prompt messages
    messages = assemble_messages(norm_payload)

    # Call LLM with schema-enforced JSON and one repair retry on invalid
    t0 = time.time()
    valid_json, model_data, llm_latency_ms, repair_attempts = call_model_with_repair(messages)
    total_latency_ms = int((time.time() - t0) * 1000)

    # Validate and reconcile response or return fallback error
    try:
        if not valid_json:
            raise ValueError("Model returned invalid JSON after repair attempt")
        # Ensure version fields present
        model_data.setdefault("version", ATTACHED_VERSIONS["api_version"]) 
        model_data.setdefault("prompt_version", ATTACHED_VERSIONS["prompt_version"]) 
        model_data.setdefault("api_version", ATTACHED_VERSIONS["api_version"]) 
        model_data.setdefault("schema_version", ATTACHED_VERSIONS["schema_version"]) 
        model_data.setdefault("request_id", request_id)
        final_resp = validate_and_reconcile(model_data, norm_payload)
        output_valid = True
    except Exception as e:
        output_valid = False
        log_json(
            _logger,
            "Rewrite failed; returning INVALID_RESPONSE",
            request_id=request_id,
            prompt_version=ATTACHED_VERSIONS["prompt_version"],
            model=OPENAI_MODEL,
            latency_ms=total_latency_ms,
            output_valid_json=False,
            retry_attempts=repair_attempts,
            error=str(e),
        )
        # Fallback
        raise HTTPException(status_code=502, detail={"error": "INVALID_RESPONSE", "request_id": request_id})

    # Observability
    metrics = compute_input_metrics(jd_core, bullets_norm)
    log_json(
        _logger,
        "Rewrite completed",
        request_id=request_id,
        prompt_version=ATTACHED_VERSIONS["prompt_version"],
        model=OPENAI_MODEL,
        latency_ms=total_latency_ms,
        llm_latency_ms=llm_latency_ms,
        output_valid_json=output_valid,
        retry_attempts=repair_attempts,
        input_length_chars=metrics["total_chars"],
        input_length_tokens=metrics["estimated_tokens"],
        grade_score=final_resp.grade.overall_score,
    )

    return final_resp


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)


