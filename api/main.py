"""FastAPI REST API for Resume Bullet Revision Service.

This API wraps the state machine orchestrator and provides endpoints for:
- Processing resumes with job descriptions
- Checking job status
- Retrieving results

Designed for integration with frontend applications (React/Next.js).
"""

from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from ulid import ULID

from ops.cost_controller import cost_controller
from ops.input_sanitizer import InputSanitizer
from ops.logging import logger
from ops.security_monitor import security_monitor
from ops.simple_rate_limiter import check_rate_limit
from orchestrator.state_machine import StateMachine
from schemas.models import JobInput, JobSettings

# Initialize rate limiter with explicit memory storage
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

# Create FastAPI app
app = FastAPI(
    title="ATS Resume Bullet Revisor API",
    description="AI-powered resume bullet revision service for ATS optimization",
    version="1.0.0",
)

# Mount static files (HTML frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

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

# In-memory job storage (replace with Redis/DB for production)
jobs_storage: dict[str, dict[str, Any]] = {}

# Initialize state machine
state_machine = StateMachine()


# === Request/Response Models ===


class ProcessResumeRequest(BaseModel):
    """Request to process a resume."""

    role: str = Field(..., min_length=1, max_length=200, description="Target job role/position")  # ✅ SECURITY: Non-empty, length limit
    jd_url: str | None = Field(None, max_length=2000, description="Job description URL")  # ✅ SECURITY: URL length limit
    jd_text: str | None = Field(None, max_length=50000, description="Job description text (if URL fails)")  # ✅ SECURITY: 50KB limit
    bullets: list[str] = Field(..., min_length=1, max_length=10, description="Resume bullets to revise")  # ✅ COST: Reduced max to 10 bullets
    extra_context: str | None = Field(None, max_length=5000, description="Additional context")  # ✅ SECURITY: 5KB limit
    settings: dict[str, Any] | None = Field(None, description="Processing settings")


class ManualJDInput(BaseModel):
    """Manual job description input when scraping fails."""

    job_id: str
    job_title: str
    company: str
    jd_text: str


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


def extract_bullets_from_text(text: str) -> list[str]:
    """Extract bullets from uploaded resume text."""
    # Simple extraction - split by newlines and filter
    lines = text.strip().split("\n")
    bullets = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
    return bullets


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


@app.get("/")
async def root():
    """Redirect to HTML frontend."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check(request: Request):
    """Detailed health check."""
    # ✅ SECURITY: Custom rate limiting (100 requests per minute)
    check_rate_limit(request, limit=100)
    """Detailed health check."""
    # Check if approaching cost limits
    is_approaching, warnings = cost_controller.is_approaching_limit()
    
    # Get security stats
    security_stats = security_monitor.get_security_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len([j for j in jobs_storage.values() if j.get("status") == "processing"]),
        "cost_warnings": warnings if is_approaching else [],
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
    resume_file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    role: str = Form(...),
    jd_url: str | None = Form(None),
    jd_text: str | None = Form(None),
    extra_context: str | None = Form(None),
):
    """
    Process a resume with a job description.

    If jd_url scraping fails, returns 422 with error details.
    Frontend should then prompt user for manual input and call /api/resume/manual-jd.
    """
    try:
        # Extract bullets from resume
        if resume_file:
            content = await resume_file.read()
            resume_content = content.decode("utf-8")
            bullets = extract_bullets_from_text(resume_content)
        elif resume_text:
            bullets = extract_bullets_from_text(resume_text)
        else:
            raise HTTPException(
                status_code=400, detail="Either resume_file or resume_text required"
            )

        if not bullets:
            raise HTTPException(status_code=400, detail="No bullets found in resume")

        # Validate JD input
        if not jd_url and not jd_text:
            raise HTTPException(status_code=400, detail="Either jd_url or jd_text required")

        # Create job
        job_id = str(ULID())

        # Try to create job input
        try:
            job_input = JobInput(
                job_id=job_id,
                role=role,
                jd_url=jd_url,
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

        return JobStatusResponse(
            job_id=job_id, status="queued", progress=0, message="Job queued for processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(stage="api", msg=f"Process resume failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resume/manual-jd", response_model=JobStatusResponse)
async def submit_manual_jd(background_tasks: BackgroundTasks, data: ManualJDInput):
    """
    Submit manual job description when scraping fails.

    This is called by frontend after user enters job details manually.
    """
    job_id = data.job_id

    # Check if job exists
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_storage[job_id]

    # Update job with manual JD
    job["jd_text"] = data.jd_text
    job["jd_source"] = "manual"
    job["job_title"] = data.job_title
    job["company"] = data.company

    # Resume processing with manual JD
    # Re-create job input with manual JD
    original_input = job.get("original_input")
    if not original_input:
        raise HTTPException(status_code=400, detail="Original input not found")

    job_input = JobInput(
        job_id=job_id,
        role=original_input["role"],
        jd_text=data.jd_text,
        jd_url=None,  # Clear URL since we have manual input
        bullets=original_input["bullets"],
        extra_context=original_input.get("extra_context"),
        settings=JobSettings(),
    )

    # Queue background task
    background_tasks.add_task(process_resume_job, job_id, job_input)
    update_job_status(job_id, "processing", 5, "Processing with manual JD...")

    return JobStatusResponse(
        job_id=job_id,
        status="processing",
        progress=5,
        message="Processing with manual job description",
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
            jd_url=data.jd_url,  # URLs are validated separately
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
