"""Pydantic models for input/output validation and internal state management."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

# ===== Input Models =====


class JobSettings(BaseModel):
    """Settings for job execution."""

    tone: str = Field(default="concise", description="Writing tone")
    max_len: int = Field(default=30, ge=1, le=100, description="Max words per bullet")
    variants: int = Field(default=2, ge=1, le=5, description="Number of variants to generate")


class JobInput(BaseModel):
    """Input schema for a resume bullet revision job."""

    role: str = Field(..., description="Target role/position")
    jd_text: str | None = Field(None, description="Job description text")
    jd_url: str | None = Field(None, description="URL to fetch JD from")
    bullets: list[str] = Field(..., min_length=1, description="Resume bullets to revise")
    metrics: dict[str, Any] | None = Field(
        None, description="Quantifiable metrics (optional, per-bullet metrics used instead)"
    )
    extra_context: str | None = Field(None, description="Additional context")
    settings: JobSettings = Field(default_factory=JobSettings)
    job_id: str | None = Field(None, description="ULID job identifier")

    @field_validator("bullets")
    @classmethod
    def bullets_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure bullets are not empty strings."""
        return [b.strip() for b in v if b.strip()]

    @field_validator("jd_text", "jd_url")
    @classmethod
    def at_least_one_jd_source(cls, v, info):
        """Ensure either jd_text or jd_url is provided."""
        # This will be checked in the state machine
        return v


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
