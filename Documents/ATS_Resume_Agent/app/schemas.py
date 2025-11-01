from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from .config import API_VERSION, PROMPT_VERSION, SCHEMA_VERSION


class ParamsModel(BaseModel):
    target_tense: Literal["present", "past", "auto"] = Field(default="auto")
    max_words_per_bullet: int = Field(default=26, ge=6, le=60)
    seniority_hint: Optional[Literal["IC mid", "Manager", "Director"]] = Field(default=None)
    request_id: Optional[str] = None
    prompt_version: str = Field(default=PROMPT_VERSION)
    api_version: str = Field(default=API_VERSION)


class RewriteRequest(BaseModel):
    job_description: str
    resume_bullets: List[str] = Field(min_length=1)
    params: ParamsModel = Field(default_factory=ParamsModel)

    @field_validator("job_description")
    @classmethod
    def jd_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("job_description is required")
        return v


class JDSignals(BaseModel):
    matched: List[str]
    missing_but_relevant: List[str]


class BulletItem(BaseModel):
    original: str
    revised: str
    word_count: int
    matched_signals: List[str]
    warnings: List[str]


class GradeSubscores(BaseModel):
    alignment: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    brevity: int = Field(ge=0, le=100)
    ats_compliance: int = Field(ge=0, le=100)


class Grade(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    letter: Literal["A", "B", "C", "D", "F"]
    subscores: GradeSubscores
    rationale: str
    suggested_global_improvements: List[str]


class RewriteResponse(BaseModel):
    version: str = Field(default=API_VERSION)
    prompt_version: str = Field(default=PROMPT_VERSION)
    api_version: str = Field(default=API_VERSION)
    schema_version: str = Field(default=SCHEMA_VERSION)
    request_id: str
    jd_signals: JDSignals
    bullets: List[BulletItem]
    grade: Grade


def response_json_schema() -> dict:
    # Minimal JSON schema for OpenAI response_format enforcement
    # It intentionally omits detailed constraints to reduce refusal risk
    return {
        "name": "ats_resume_rewrite_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "version": {"type": "string"},
                "prompt_version": {"type": "string"},
                "api_version": {"type": "string"},
                "schema_version": {"type": "string"},
                "request_id": {"type": "string"},
                "jd_signals": {
                    "type": "object",
                    "properties": {
                        "matched": {"type": "array", "items": {"type": "string"}},
                        "missing_but_relevant": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["matched", "missing_but_relevant"],
                    "additionalProperties": False,
                },
                "bullets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "string"},
                            "revised": {"type": "string"},
                            "word_count": {"type": "integer"},
                            "matched_signals": {"type": "array", "items": {"type": "string"}},
                            "warnings": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "original",
                            "revised",
                            "word_count",
                            "matched_signals",
                            "warnings",
                        ],
                        "additionalProperties": False,
                    },
                },
                "grade": {
                    "type": "object",
                    "properties": {
                        "overall_score": {"type": "integer"},
                        "letter": {"type": "string"},
                        "subscores": {
                            "type": "object",
                            "properties": {
                                "alignment": {"type": "integer"},
                                "impact": {"type": "integer"},
                                "clarity": {"type": "integer"},
                                "brevity": {"type": "integer"},
                                "ats_compliance": {"type": "integer"},
                            },
                            "required": ["alignment", "impact", "clarity", "brevity", "ats_compliance"],
                            "additionalProperties": False,
                        },
                        "rationale": {"type": "string"},
                        "suggested_global_improvements": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "overall_score",
                        "letter",
                        "subscores",
                        "rationale",
                        "suggested_global_improvements",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": [
                "version",
                "prompt_version",
                "api_version",
                "schema_version",
                "request_id",
                "jd_signals",
                "bullets",
                "grade",
            ],
        },
        "strict": True,
    }


