"""SHA256 hashing utilities for idempotency keys and content hashing."""

import hashlib
import json
from typing import Any


def compute_sha256(content: str) -> str:
    """
    Compute SHA256 hash of a string.

    Args:
        content: String to hash

    Returns:
        str: Hex-encoded SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_jd_hash(jd_text: str) -> str:
    """
    Compute a hash of normalized JD text.

    Args:
        jd_text: Job description text

    Returns:
        str: SHA256 hash of normalized text
    """
    normalized = jd_text.strip().lower()
    return compute_sha256(normalized)


def compute_idempotency_key(
    job_id: str, jd_hash: str, bullets: list[str], settings: dict[str, Any]
) -> str:
    """
    Compute idempotency key for a job.

    Formula: sha256(job_id + jd_hash + join(bullets) + stringify(settings))

    Args:
        job_id: Unique job identifier
        jd_hash: Hash of the job description
        bullets: List of resume bullets
        settings: Job settings dictionary

    Returns:
        str: SHA256 hash to use as idempotency key
    """
    bullets_joined = "||".join(bullets)
    settings_str = json.dumps(settings, sort_keys=True)

    combined = f"{job_id}::{jd_hash}::{bullets_joined}::{settings_str}"
    return compute_sha256(combined)
