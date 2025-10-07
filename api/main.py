"""FastAPI REST API for Resume Bullet Revision Service.

This API wraps the state machine orchestrator and provides endpoints for:
- Processing resumes with job descriptions
- Checking job status
- Retrieving results

Designed for integration with frontend applications (React/Next.js).
"""

from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ulid import ULID

from ops.logging import logger
from orchestrator.state_machine import StateMachine
from schemas.models import JobInput, JobSettings

# Create FastAPI app
app = FastAPI(
    title="ATS Resume Bullet Revisor API",
    description="AI-powered resume bullet revision service for ATS optimization",
    version="1.0.0",
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (replace with Redis/DB for production)
jobs_storage: dict[str, dict[str, Any]] = {}

# Initialize state machine
state_machine = StateMachine()


# === Request/Response Models ===


class ProcessResumeRequest(BaseModel):
    """Request to process a resume."""

    role: str = Field(..., description="Target job role/position")
    jd_url: str | None = Field(None, description="Job description URL")
    jd_text: str | None = Field(None, description="Job description text (if URL fails)")
    bullets: list[str] = Field(..., description="Resume bullets to revise")
    extra_context: str | None = Field(None, description="Additional context")
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
        result = state_machine.run(job_input)

        # Store result
        jobs_storage[job_id]["result"] = result.model_dump()
        update_job_status(job_id, "completed", 100, "Processing complete")

    except Exception as e:
        logger.error(stage="api", msg=f"Job {job_id} failed: {str(e)}")
        update_job_status(job_id, "failed", error=str(e))


# === API Endpoints ===


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "ATS Resume Bullet Revisor API", "status": "healthy", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len([j for j in jobs_storage.values() if j.get("status") == "processing"]),
    }


@app.post("/api/resume/process", response_model=JobStatusResponse)
async def process_resume(
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
async def process_sync(request: ProcessResumeRequest):
    """
    Synchronous processing endpoint (for testing only).

    WARNING: This will timeout for long-running jobs. Use async endpoints in production.
    """
    try:
        job_id = str(ULID())

        job_input = JobInput(
            job_id=job_id,
            role=request.role,
            jd_url=request.jd_url,
            jd_text=request.jd_text,
            bullets=request.bullets,
            extra_context=request.extra_context,
            settings=JobSettings(**(request.settings or {})),
        )

        result = state_machine.run(job_input)

        return result.model_dump()

    except Exception as e:
        logger.error(stage="api", msg=f"Sync processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
