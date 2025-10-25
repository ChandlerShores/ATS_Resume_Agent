"""Pydantic models for input/output validation and internal state management."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ===== Input Models =====


class JobSettings(BaseModel):
    """Settings for job execution."""

    tone: str = Field(default="concise", description="Writing tone")
    max_len: int = Field(default=30, ge=1, le=100, description="Max words per bullet")
    variants: int = Field(default=1, ge=1, le=3, description="Number of variants to generate")  # REDUCED: Default 1, max 3


class JobInput(BaseModel):
    """Input schema for a resume bullet revision job."""

    role: str = Field(..., max_length=200, description="Target role/position")  # ✅ SECURITY: Length limit
    jd_text: str = Field(..., max_length=50000, description="Job description text")  # ✅ SECURITY: 50KB limit
    bullets: list[str] = Field(..., min_length=1, max_length=20, description="Resume bullets to revise")  # ✅ SECURITY: Max 20 bullets
    metrics: dict[str, Any] | None = Field(
        None, description="Quantifiable metrics (optional, per-bullet metrics used instead)"
    )
    extra_context: str | None = Field(None, max_length=5000, description="Additional context")  # ✅ SECURITY: 5KB limit
    settings: JobSettings = Field(default_factory=JobSettings)
    job_id: str | None = Field(None, description="ULID job identifier")

    @field_validator("bullets")
    @classmethod
    def bullets_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure bullets are not empty strings and limit individual length."""
        # ✅ SECURITY: Limit individual bullet length to 1KB
        cleaned_bullets = []
        for bullet in v:
            if bullet and bullet.strip():
                # Limit each bullet to 1000 characters
                cleaned_bullet = bullet.strip()[:1000]
                cleaned_bullets.append(cleaned_bullet)
        return cleaned_bullets



# ===== Output Models =====


class Coverage(BaseModel):
    """Coverage analysis of JD terms."""

    hit: list[str] = Field(default_factory=list, description="Terms covered in bullets")
    miss: list[str] = Field(default_factory=list, description="Terms missing from bullets")


class Summary(BaseModel):
    """Job summary with role and coverage information."""

    role: str
    top_terms: list[str] = Field(default_factory=list)
    coverage: Coverage = Field(default_factory=Coverage)


class BulletScores(BaseModel):
    """Scores for a revised bullet."""

    relevance: int = Field(..., ge=0, le=100, description="JD alignment score")
    impact: int = Field(..., ge=0, le=100, description="Impact/outcome score")
    clarity: int = Field(..., ge=0, le=100, description="Clarity score")


class BulletDiff(BaseModel):
    """Differences between original and revised bullet."""

    removed: list[str] = Field(default_factory=list, description="Removed terms/phrases")
    added_terms: list[str] = Field(default_factory=list, description="Added JD-aligned terms")


class BulletResult(BaseModel):
    """Result for a single revised bullet."""

    original: str
    revised: list[str] = Field(default_factory=list, description="Revised variants")
    scores: BulletScores
    notes: str = Field(..., description="Brief explanation of changes")
    diff: BulletDiff = Field(default_factory=BulletDiff)


class LogEntry(BaseModel):
    """Structured log entry."""

    ts: str = Field(..., description="ISO 8601 timestamp")
    level: str = Field(..., description="Log level: info, warn, error")
    stage: str = Field(..., description="State machine stage")
    msg: str = Field(..., description="Log message")
    job_id: str | None = Field(None, description="Job identifier")


class JobOutput(BaseModel):
    """Output schema for a completed job."""

    job_id: str
    summary: Summary
    results: list[BulletResult]
    red_flags: list[str] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)


# ===== Internal State Models =====


class JDSignals(BaseModel):
    """Extracted signals from job description."""

    top_terms: list[str] = Field(default_factory=list, description="Prioritized keywords")
    weights: dict[str, float] = Field(default_factory=dict, description="Term importance weights")
    synonyms: dict[str, list[str]] = Field(default_factory=dict, description="Synonym map")
    themes: dict[str, list[str]] = Field(default_factory=dict, description="Thematic groupings")

    # Categorized keywords for intelligent keyword usage
    soft_skills: list[str] = Field(
        default_factory=list, description="Transferable skills (analytical thinking, adaptability)"
    )
    hard_tools: list[str] = Field(
        default_factory=list, description="Specific tools/platforms (Marketo, Salesforce)"
    )
    domain_terms: list[str] = Field(
        default_factory=list, description="Industry/context terms (B2B healthcare, SaaS)"
    )


class RewriteVariant(BaseModel):
    """A single rewrite variant with rationale."""

    text: str = Field(..., max_length=500)
    rationale: str = Field(..., description="Brief explanation")


class ValidationResult(BaseModel):
    """Result of validation checks."""

    ok: bool = Field(..., description="Overall validation status")
    flags: list[str] = Field(default_factory=list, description="Issues found")
    fixes: list[str] = Field(default_factory=list, description="Applied fixes")


# ===== State Machine Internal State =====


class JobState(BaseModel):
    """Internal state passed between state machine stages."""

    job_id: str
    input_data: JobInput
    jd_text: str = ""
    jd_hash: str = ""
    normalized_bullets: list[str] = Field(default_factory=list)

    # Categorized bullets
    achievement_bullets: list[str] = Field(
        default_factory=list, description="Bullets to fully rewrite"
    )
    skill_bullets: list[str] = Field(default_factory=list, description="Bullets to lightly format")
    metadata_bullets: list[str] = Field(default_factory=list, description="Bullets to preserve")

    jd_signals: JDSignals | None = None
    raw_rewrites: dict[str, list[RewriteVariant]] = Field(default_factory=dict)
    scored_results: list[BulletResult] = Field(default_factory=list)
    validation_results: dict[str, ValidationResult] = Field(default_factory=dict)
    red_flags: list[str] = Field(default_factory=list)
    logs: list[dict[str, Any]] = Field(default_factory=list)

    def add_log(self, log_entry: dict[str, Any]):
        """Add a log entry to the state."""
        self.logs.append(log_entry)


# ===== Bulk Processing Models =====

class CandidateInput(BaseModel):
    """Input for a single candidate in bulk processing."""
    
    candidate_id: str = Field(..., max_length=100, description="Unique candidate identifier")
    bullets: list[str] = Field(..., min_length=1, max_length=20, description="Resume bullets to revise")
    
    @field_validator("bullets")
    @classmethod
    def bullets_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure bullets are not empty strings and limit individual length."""
        cleaned_bullets = []
        for bullet in v:
            if bullet and bullet.strip():
                # Limit each bullet to 1000 characters
                cleaned_bullet = bullet.strip()[:1000]
                cleaned_bullets.append(cleaned_bullet)
        return cleaned_bullets


class BulkProcessRequest(BaseModel):
    """Request schema for bulk resume processing."""
    
    job_description: str = Field(..., max_length=50000, description="Job description text")
    candidates: list[CandidateInput] = Field(..., min_length=1, max_length=50, description="List of candidates to process")
    settings: JobSettings = Field(default_factory=JobSettings)


class CandidateResult(BaseModel):
    """Result for a single candidate in bulk processing."""
    
    candidate_id: str
    status: str = Field(..., description="processing|completed|failed")
    results: list[BulletResult] = Field(default_factory=list)
    coverage: Coverage | None = None
    error_message: str | None = None


class BulkProcessResponse(BaseModel):
    """Response schema for bulk processing status/results."""
    
    job_id: str
    status: str = Field(..., description="processing|completed|failed")
    total_candidates: int
    processed_candidates: int
    candidates: list[CandidateResult] = Field(default_factory=list)
    error_message: str | None = None


# ===== Customer Management Models =====

class Customer(BaseModel):
    """Customer model for API key management."""
    
    customer_id: str = Field(..., description="Unique customer identifier")
    api_key: str = Field(..., description="API key for authentication")
    name: str = Field(..., description="Customer name")
    is_active: bool = Field(default=True, description="Whether customer is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class UsageRecord(BaseModel):
    """Usage tracking record for a customer on a specific date."""
    
    customer_id: str = Field(..., description="Customer identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    request_count: int = Field(default=0, description="Number of requests on this date")
    total_bullets: int = Field(default=0, description="Total bullets processed on this date")
    last_request: datetime = Field(default_factory=datetime.utcnow, description="Last request timestamp")