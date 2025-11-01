import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from .config import LOG_LEVEL, REDACT_PII_IN_LOGS


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=True)


_email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_phone_re = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(\d{3}\)|\d{3})[\s-]?\d{3}[\s-]?\d{4}")
_url_re = re.compile(r"https?://[^\s]+")


def redact_pii(text: str) -> str:
    if not REDACT_PII_IN_LOGS:
        return text
    text = _email_re.sub("[REDACTED_EMAIL]", text)
    text = _phone_re.sub("[REDACTED_PHONE]", text)
    text = _url_re.sub("[REDACTED_URL]", text)
    return text


def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_json(logger: logging.Logger, message: str, **fields: Any) -> None:
    safe_fields: Dict[str, Any] = {}
    for k, v in fields.items():
        if isinstance(v, str):
            safe_fields[k] = redact_pii(v)
        else:
            safe_fields[k] = v
    logger.info(redact_pii(message), extra={"extra": safe_fields})


