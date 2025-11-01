import hashlib
import json
import os
import re
from typing import Dict, List, Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

from .config import REDIS_URL, REDIS_TTL_SECONDS


_TOOL_HINTS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "sql",
    "snowflake",
    "spark",
    "hadoop",
    "react",
    "node",
    "fastapi",
    "django",
    "flask",
]

_COMPETENCY_HINTS = [
    "leadership",
    "mentorship",
    "stakeholder",
    "cross-functional",
    "communication",
    "ownership",
    "scalability",
    "reliability",
    "performance",
    "security",
]


def _hash_key(jd: str) -> str:
    return hashlib.sha256(jd.encode("utf-8")).hexdigest()


def _connect_redis():
    if not REDIS_URL or not redis:
        return None
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_\-\+\.]{1,32}", text.lower())


def extract_jd_signals(jd: str) -> Dict[str, List[str]]:
    tokens = _tokenize(jd)
    skills = sorted({t for t in tokens if t in _TOOL_HINTS})
    competencies = sorted({t for t in tokens if t in _COMPETENCY_HINTS})
    # naive noun-like tokens as additional signals
    common_stop = {
        "and",
        "or",
        "the",
        "a",
        "to",
        "of",
        "in",
        "for",
        "with",
        "on",
        "as",
        "by",
        "is",
        "are",
    }
    tools = skills
    extra = sorted({t for t in tokens if len(t) > 2 and t not in common_stop})
    return {
        "skills": skills,
        "tools": tools,
        "competencies": competencies,
        "keywords": extra[:50],
    }


def get_cached_signals(jd: str) -> Dict[str, List[str]]:
    key = f"jd_signals:{_hash_key(jd)}"
    client = _connect_redis()
    if client:
        cached = client.get(key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass
        value = extract_jd_signals(jd)
        try:
            client.setex(key, REDIS_TTL_SECONDS, json.dumps(value))
        except Exception:
            pass
        return value
    # fallback in-memory no-cache
    return extract_jd_signals(jd)


