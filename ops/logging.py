"""Structured logging utility for consistent log formatting across the application."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class StructuredLogger:
    """Logger that outputs structured JSON logs with job_id correlation."""

    def __init__(self, name: str = "ats_resume_agent"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def _format_log(
        self, level: str, stage: str, msg: str, job_id: str | None = None, **extra: Any
    ) -> str:
        """Format a log entry as JSON."""
        log_entry: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": level,
            "stage": stage,
            "msg": msg,
        }

        if job_id:
            log_entry["job_id"] = job_id

        if extra:
            log_entry.update(extra)

        return json.dumps(log_entry)

    def info(self, stage: str, msg: str, job_id: str | None = None, **extra: Any) -> dict[str, Any]:
        """Log an info-level message."""
        log_str = self._format_log("info", stage, msg, job_id, **extra)
        self.logger.info(log_str)
        return json.loads(log_str)

    def warn(self, stage: str, msg: str, job_id: str | None = None, **extra: Any) -> dict[str, Any]:
        """Log a warning-level message."""
        log_str = self._format_log("warn", stage, msg, job_id, **extra)
        self.logger.warning(log_str)
        return json.loads(log_str)

    def error(
        self, stage: str, msg: str, job_id: str | None = None, **extra: Any
    ) -> dict[str, Any]:
        """Log an error-level message."""
        log_str = self._format_log("error", stage, msg, job_id, **extra)
        self.logger.error(log_str)
        return json.loads(log_str)


# Global logger instance
logger = StructuredLogger()
