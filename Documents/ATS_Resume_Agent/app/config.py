import os
from typing import Optional


PROMPT_VERSION: str = os.getenv("PROMPT_VERSION", "1.0.0")
API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
SCHEMA_VERSION: str = os.getenv("SCHEMA_VERSION", "2025-11-01")

# OpenAI
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
OPENAI_TIMEOUT_SECONDS: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))

# Service limits/configs
GLOBAL_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
GLOBAL_MAX_WORDS_PER_BULLET_DEFAULT: int = int(os.getenv("MAX_WORDS_PER_BULLET_DEFAULT", "26"))

# Optional Redis cache for JD signals
REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL_SECONDS", "86400"))  # 1 day

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
REDACT_PII_IN_LOGS: bool = os.getenv("REDACT_PII_IN_LOGS", "true").lower() == "true"

# Versions block to attach to responses
ATTACHED_VERSIONS = {
    "prompt_version": PROMPT_VERSION,
    "api_version": API_VERSION,
    "schema_version": SCHEMA_VERSION,
}


