"""FastAPI REST API for Resume Bullet Revision Service.

This API wraps the state machine orchestrator and provides endpoints for:
- Processing resumes with job descriptions
- Checking job status
- Retrieving results

Designed for integration with frontend applications (React/Next.js).
"""

from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from ulid import ULID

from ops.cost_controller import cost_controller
from ops.customer_manager import customer_manager
from ops.input_sanitizer import InputSanitizer
from ops.logging import logger
from ops.security_monitor import security_monitor
from ops.simple_rate_limiter import check_rate_limit
from orchestrator.state_machine import StateMachine
from schemas.models import (
    BulkProcessRequest,
    BulkProcessResponse,
    CandidateResult,
    JobInput,
    JobSettings,
)

# Initialize rate limiter with explicit memory storage
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

# Create FastAPI app
app = FastAPI(
    title="ATS Resume Bullet Revisor API",
    description="AI-powered resume bullet revision service for ATS optimization",
    version="1.0.0",
)


# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration for frontend integration
import os

# Environment-based CORS - configure ALLOWED_ORIGINS in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    # Development default - change for production
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ SECURITY: Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # ✅ SECURITY: Limited methods
    allow_headers=["Content-Type"],  # ✅ SECURITY: Limited headers
)


# ✅ SECURITY: Request size limiting middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request body size to prevent memory exhaustion attacks."""
    if request.method == "POST":
        # Read the body to check size
        body = await request.body()
        
        # 10MB limit
        max_size = 10 * 1024 * 1024  # 10MB
        if len(body) > max_size:
            logger.warn(
                stage="api",
                msg="Request too large",
                size=len(body),
                max_size=max_size,
                client_ip=request.client.host
            )
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large. Maximum size is 10MB."}
            )
        
        # Recreate request with body for downstream processing
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
    
    response = await call_next(request)
    return response


# ✅ SECURITY: Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response


# ✅ SECURITY: API Key validation middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Validate API key for all requests except health check."""
    # Skip API key validation for health check
    if request.url.path == "/health":
        return await call_next(request)
    
    # Extract API key from header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        logger.warn(
            stage="api",
            msg="Request without API key",
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "API key required. Include X-API-Key header."}
        )
    
    try:
        # Validate API key and get customer ID
        customer_id = customer_manager.validate_api_key(api_key)
        request.state.customer_id = customer_id
        
        logger.info(
            stage="api",
            msg="API key validated",
            customer_id=customer_id,
            path=request.url.path
        )
        
    except ValueError as e:
        logger.warn(
            stage="api",
            msg="Invalid API key",
            error=str(e),
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key"}
        )
    
    response = await call_next(request)
    return response


# In-memory job storage (replace with Redis/DB for production)
jobs_storage: dict[str, dict[str, Any]] = {}

# Initialize state machine
state_machine = StateMachine()


# === Request/Response Models ===


class ProcessResumeRequest(BaseModel):
    """Request to process a resume (testing/dev endpoint)."""

    role: str = Field(..., min_length=1, max_length=200, description="Target job role/position")  # ✅ SECURITY: Non-empty, length limit
    jd_text: str = Field(..., max_length=50000, description="Job description text")  # ✅ SECURITY: 50KB limit
    bullets: list[str] = Field(..., min_length=1, max_length=10, description="Resume bullets to revise")  # ✅ COST: Reduced max to 10 bullets
    extra_context: str | None = Field(None, max_length=5000, description="Additional context")  # ✅ SECURITY: 5KB limit
    settings: dict[str, Any] | None = Field(None, description="Processing settings")




class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    status: str  # "processing", "completed", "failed"
    progress: int | None = None  # 0-100
    message: str | None = None
    error: str | None = None


class JobResultResponse(BaseModel):
    """Job result response."""

    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


# === Helper Functions ===


def update_job_status(
    job_id: str, status: str, progress: int = None, message: str = None, error: str = None
):
    """Update job status in storage."""
    if job_id not in jobs_storage:
        jobs_storage[job_id] = {}

    jobs_storage[job_id].update(
        {
            "status": status,
            "progress": progress,
            "message": message,
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
        }
    )


def process_resume_job(job_id: str, job_input: JobInput):
    """Background task to process resume."""
    try:
        update_job_status(job_id, "processing", 10, "Starting ingestion...")

        # Run state machine
        result = state_machine.execute(job_input.model_dump())

        # Store result
        jobs_storage[job_id]["result"] = result
        update_job_status(job_id, "completed", 100, "Processing complete")

    except Exception as e:
        logger.error(stage="api", msg=f"Job {job_id} failed: {str(e)}")
        update_job_status(job_id, "failed", error=str(e))


# === API Endpoints ===




@app.get("/health")
async def health_check(request: Request):
    """Detailed health check."""
    # ✅ SECURITY: Custom rate limiting (100 requests per minute)
    check_rate_limit(request, limit=100)
    
    # Check if approaching cost limits
    is_approaching, warnings = cost_controller.is_approaching_limit()
    
    # Get security stats
    security_stats = security_monitor.get_security_stats()
    
    # Get customer stats
    customer_stats = customer_manager.get_all_customers_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len([j for j in jobs_storage.values() if j.get("status") == "processing"]),
        "cost_warnings": warnings if is_approaching else [],
        "customers": customer_stats,
        "security": {
            "suspicious_ips": security_stats["suspicious_ips"],
            "total_failed_attempts": security_stats["total_failed_attempts"],
            "total_suspicious_patterns": security_stats["total_suspicious_patterns"]
        }
    }


@app.post("/api/resume/process", response_model=JobStatusResponse)
@limiter.limit("5/minute")  # ✅ SECURITY: Rate limit expensive operations
async def process_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    resume_text: str = Form(...),
    role: str = Form(...),
    jd_text: str = Form(...),
    extra_context: str | None = Form(None),
):
    """
    Process a single resume with a job description (Testing/Dev endpoint).
    
    NOTE: For production use, please use /api/bulk/process endpoint.
    This endpoint accepts manual text input only - no file uploads or URL scraping.
    """
    try:
        # Parse bullets from resume text (simple newline split)
        bullets = [line.strip() for line in resume_text.strip().split("\n") if line.strip() and len(line.strip()) > 10]

        if not bullets:
            raise HTTPException(status_code=400, detail="No bullets found in resume text")

        # Create job
        job_id = str(ULID())

        # Try to create job input
        try:
            job_input = JobInput(
                job_id=job_id,
                role=role,
                jd_text=jd_text,
                bullets=bullets,
                extra_context=extra_context,
                settings=JobSettings(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

        # Initialize job storage
        jobs_storage[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Queue background task
        background_tasks.add_task(process_resume_job, job_id, job_input)
        
        # Track usage
        customer_id = request.state.customer_id
        bullets_count = len(bullets)
        customer_manager.track_usage(customer_id, bullets_count)
        
        logger.info(
            stage="api",
            msg="Resume processing started",
            job_id=job_id,
            customer_id=customer_id,
            bullets_count=bullets_count
        )

        return JobStatusResponse(
            job_id=job_id, status="queued", progress=0, message="Job queued for processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(stage="api", msg=f"Process resume failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bulk/process", response_model=BulkProcessResponse)
@limiter.limit("5/minute")
async def bulk_process_resumes(
    request: Request,
    background_tasks: BackgroundTasks,
    data: BulkProcessRequest,
):
    """
    Process multiple candidates' resumes against a single job description.
    
    This is the primary B2B endpoint for bulk resume processing.
    """
    from ops.cost_controller import cost_controller
    from ops.input_sanitizer import InputSanitizer
    from ops.logging import logger
    from ops.security_monitor import security_monitor
    
    # Security checks
    sanitizer = InputSanitizer()
    if not sanitizer.is_safe_input(data.job_description):
        security_monitor.log_suspicious_activity(request.client.host, "suspicious_jd")
        raise HTTPException(status_code=400, detail="Suspicious input detected")
    
    # Cost check
    if not cost_controller.can_make_request():
        raise HTTPException(status_code=429, detail="Daily cost limit exceeded")
    
    # Generate job ID
    job_id = str(ULID())
    
    # Initialize bulk job storage
    jobs_storage[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "total_candidates": len(data.candidates),
        "processed_candidates": 0,
        "candidates": {},
        "created_at": datetime.utcnow(),
        "job_description": data.job_description,
        "settings": data.settings.dict(),
    }
    
    # Track usage
    customer_id = request.state.customer_id
    total_bullets = sum(len(candidate.bullets) for candidate in data.candidates)
    customer_manager.track_usage(customer_id, total_bullets)
    
    # Start background processing
    background_tasks.add_task(process_bulk_job, job_id, data)
    
    logger.info(
        stage="api",
        msg="Bulk processing started",
        job_id=job_id,
        customer_id=customer_id,
        total_candidates=len(data.candidates),
        total_bullets=total_bullets,
        jd_length=len(data.job_description)
    )
    
    return BulkProcessResponse(
        job_id=job_id,
        status="processing",
        total_candidates=len(data.candidates),
        processed_candidates=0,
        candidates=[]
    )


async def process_bulk_job(job_id: str, data: BulkProcessRequest):
    """Process bulk job in background."""
    from ops.logging import logger
    
    try:
        state_machine = StateMachine()
        candidates = {}
        
        # Process each candidate
        for candidate in data.candidates:
            try:
                # Create JobInput for this candidate
                job_input = JobInput(
                    job_id=f"{job_id}_{candidate.candidate_id}",
                    role="Target Role",  # Could be extracted from JD in future
                    jd_text=data.job_description,
                    bullets=candidate.bullets,
                    settings=data.settings,
                )
                
                # Execute state machine for this candidate
                result = state_machine.execute(job_input)
                
                # Store candidate result
                candidates[candidate.candidate_id] = {
                    "candidate_id": candidate.candidate_id,
                    "status": "completed",
                    "results": result.bullet_results,
                    "coverage": result.coverage,
                    "error_message": None,
                }
                
                # Update progress
                jobs_storage[job_id]["processed_candidates"] += 1
                jobs_storage[job_id]["candidates"] = candidates
                
                logger.info(
                    stage="api",
                    msg="Candidate processed",
                    job_id=job_id,
                    candidate_id=candidate.candidate_id,
                    bullets_count=len(candidate.bullets)
                )
                
            except Exception as e:
                # Handle individual candidate failure
                candidates[candidate.candidate_id] = {
                    "candidate_id": candidate.candidate_id,
                    "status": "failed",
                    "results": [],
                    "coverage": None,
                    "error_message": str(e),
                }
                
                jobs_storage[job_id]["processed_candidates"] += 1
                jobs_storage[job_id]["candidates"] = candidates
                
                logger.error(
                    stage="api",
                    msg=f"Candidate processing failed: {str(e)}",
                    job_id=job_id,
                    candidate_id=candidate.candidate_id
                )
        
        # Mark job as completed
        jobs_storage[job_id]["status"] = "completed"
        jobs_storage[job_id]["completed_at"] = datetime.utcnow()
        
        logger.info(
            stage="api",
            msg="Bulk processing completed",
            job_id=job_id,
            total_candidates=len(data.candidates),
            processed_candidates=jobs_storage[job_id]["processed_candidates"]
        )
        
    except Exception as e:
        # Handle overall job failure
        jobs_storage[job_id]["status"] = "failed"
        jobs_storage[job_id]["error"] = str(e)
        jobs_storage[job_id]["failed_at"] = datetime.utcnow()
        
        logger.error(
            stage="api",
            msg=f"Bulk processing failed: {str(e)}",
            job_id=job_id
        )


@app.get("/api/bulk/status/{job_id}", response_model=BulkProcessResponse)
async def get_bulk_job_status(job_id: str):
    """Get bulk job processing status."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    # Convert candidates dict to list
    candidates = []
    for candidate_data in job.get("candidates", {}).values():
        candidates.append(CandidateResult(**candidate_data))
    
    return BulkProcessResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        total_candidates=job.get("total_candidates", 0),
        processed_candidates=job.get("processed_candidates", 0),
        candidates=candidates,
        error_message=job.get("error")
    )


@app.get("/api/bulk/results/{job_id}", response_model=BulkProcessResponse)
async def get_bulk_job_results(job_id: str):
    """Get bulk job results when processing is complete."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    status = job.get("status")
    
    if status == "processing":
        raise HTTPException(status_code=202, detail="Job still processing")
    
    # Convert candidates dict to list
    candidates = []
    for candidate_data in job.get("candidates", {}).values():
        candidates.append(CandidateResult(**candidate_data))
    
    return BulkProcessResponse(
        job_id=job_id,
        status=status,
        total_candidates=job.get("total_candidates", 0),
        processed_candidates=job.get("processed_candidates", 0),
        candidates=candidates,
        error_message=job.get("error")
    )


@app.get("/api/resume/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job processing status."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_storage[job_id]

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress"),
        message=job.get("message"),
        error=job.get("error"),
    )


@app.get("/api/resume/result/{job_id}", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Get job result when processing is complete."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_storage[job_id]
    status = job.get("status")

    if status == "processing" or status == "queued":
        return JobResultResponse(job_id=job_id, status=status, error="Job still processing")

    if status == "failed":
        return JobResultResponse(
            job_id=job_id, status=status, error=job.get("error", "Unknown error")
        )

    if status == "completed":
        return JobResultResponse(job_id=job_id, status=status, result=job.get("result"))

    raise HTTPException(status_code=500, detail="Unknown job status")


@app.delete("/api/resume/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs_storage[job_id]

    return {"message": "Job deleted successfully"}


# === Development/Testing Endpoints ===


@app.post("/api/test/process-sync")
async def process_sync(request: Request, data: ProcessResumeRequest):
    """Process resume bullets synchronously with security controls."""
    # ✅ SECURITY: Custom rate limiting (5 requests per minute)
    print(f"DEBUG: Checking rate limit for IP: {request.client.host if request.client else 'unknown'}")
    check_rate_limit(request, limit=5)
    print("DEBUG: Rate limit check passed")
    """
    Synchronous processing endpoint (for testing only).

    WARNING: This will timeout for long-running jobs. Use async endpoints in production.
    """
    try:
        # ✅ SECURITY: Check cost limits before processing
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        is_allowed, reason = cost_controller.check_cost_limit(model)
        if not is_allowed:
            logger.warn(
                stage="api",
                msg="Request blocked by cost controller",
                reason=reason,
                client_ip=request.client.host
            )
            raise HTTPException(status_code=429, detail=f"Request blocked: {reason}")
        
        # ✅ SECURITY: Sanitize all inputs before processing
        sanitized_role = InputSanitizer.sanitize_role(data.role)
        sanitized_jd_text = InputSanitizer.sanitize_job_description(data.jd_text) if data.jd_text else None
        sanitized_bullets = InputSanitizer.sanitize_bullets(data.bullets)
        sanitized_context = InputSanitizer.sanitize_extra_context(data.extra_context) if data.extra_context else None
        
        # Check for suspicious patterns
        is_safe, warnings = InputSanitizer.is_safe_input(data.jd_text or "")
        if not is_safe:
            # ✅ SECURITY: Log suspicious patterns to security monitor
            for warning in warnings:
                security_monitor.log_suspicious_pattern(
                    ip=request.client.host,
                    pattern=warning,
                    input_type="jd_text"
                )
            
            logger.warn(
                stage="api",
                msg="Suspicious input detected",
                warnings=warnings,
                client_ip=request.client.host
            )
        
        if not sanitized_bullets:
            raise HTTPException(status_code=400, detail="No valid bullets provided after sanitization")
        
        job_id = str(ULID())

        job_input = JobInput(
            job_id=job_id,
            role=sanitized_role,
            jd_text=sanitized_jd_text,
            bullets=sanitized_bullets,
            extra_context=sanitized_context,
            settings=JobSettings(**(data.settings or {})),
        )

        result = state_machine.execute(job_input.model_dump())

        # ✅ SECURITY: Track successful request for cost monitoring
        cost_controller.track_request(model)
        
        return result

    except Exception as e:
        logger.error(stage="api", msg=f"Sync processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ SECURITY: Global exception handler to sanitize error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that sanitizes error messages."""
    client_ip = request.client.host if request.client else "unknown"
    
    # ✅ SECURITY: Log failed requests to security monitor
    security_monitor.log_failed_request(
        ip=client_ip,
        reason=str(exc),
        endpoint=request.url.path
    )
    
    # Log the full error for debugging
    logger.error(
        stage="api",
        msg=f"Unhandled error: {str(exc)}",
        error_type=type(exc).__name__,
        client_ip=client_ip
    )
    
    # Return sanitized error message to client
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
