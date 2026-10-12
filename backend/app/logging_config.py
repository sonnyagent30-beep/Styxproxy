"""Standard library logging configuration for Styxproxy backend.

The backend uses two logging systems:
- structlog (configured in main.py) for the app's own logger
- stdlib logging for most routers and services

This module configures stdlib logging so that `extra={...}` fields
are actually rendered in the output. Without this, the default root
logger format ``%(levelname)s:%(name)s:%(message)s`` silently drops
all extra fields.
"""
import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """JSON formatter that includes all extra fields.

    Produces one JSON object per log line, suitable for Datadog
    and other structured log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Collect all extra fields (attributes not in the default LogRecord)
        default_attrs = logging.LogRecord(
            None, None, None, None, None, None, None
        ).__dict__
        for key, value in record.__dict__.items():
            if key not in default_attrs and not key.startswith("_"):
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger and uvicorn loggers with JSON formatting.

    This ensures that all stdlib logging calls with ``extra={...}`` fields
    have those fields rendered in the output.
    """
    formatter = JsonFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stderr handler (captured by systemd as StandardError)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # Configure uvicorn loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = False
        uvicorn_logger.addHandler(stderr_handler)
