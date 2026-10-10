"""Test that stdlib logging with extra= fields renders those fields.

This is the acceptance test for the logging fix: before the fix,
`logger.error("msg", extra={"error": "boom"})` would produce a log line
containing only "msg" — the extra fields were silently dropped by the
default root logger format.

After the fix, the JSON formatter includes all extra fields.
"""
import json
import logging
import sys

import pytest

from app.logging_config import configure_logging, JsonFormatter


class TestExtraFieldsRendered:
    """Verify that extra= fields appear in log output."""

    def test_json_formatter_includes_extra_fields(self):
        """JsonFormatter should include all extra fields in the JSON output."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="basket order creation failed",
            args=(),
            exc_info=None,
        )
        # Simulate extra fields
        record.error = "plan_code overflow"
        record.error_type = "ValueError"
        record.order_id = "ord_123"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "basket order creation failed"
        assert data["level"] == "ERROR"
        assert data["logger"] == "test.logger"
        assert data["error"] == "plan_code overflow"
        assert data["error_type"] == "ValueError"
        assert data["order_id"] == "ord_123"

    def test_configure_logging_adds_json_handler(self):
        """configure_logging should add a handler that renders extra fields."""
        configure_logging(level="DEBUG")

        root = logging.getLogger()
        assert len(root.handlers) > 0
        assert any(
            isinstance(h.formatter, JsonFormatter) for h in root.handlers
        )

    def test_extra_fields_in_stderr_output(self, capsys):
        """After configure_logging, extra fields should appear in stderr output."""
        configure_logging(level="DEBUG")

        logger = logging.getLogger("test.stderr_output")
        logger.error(
            "basket order creation failed",
            extra={"error": "plan_code overflow", "error_type": "ValueError"},
        )

        captured = capsys.readouterr()
        output = captured.err.strip()
        assert output, "Expected log output on stderr"

        # The output should be valid JSON containing the extra fields
        data = json.loads(output)
        assert data["message"] == "basket order creation failed"
        assert data["error"] == "plan_code overflow"
        assert data["error_type"] == "ValueError"

    def test_uvicorn_loggers_configured(self):
        """Uvicorn loggers should also use the JSON formatter."""
        configure_logging(level="INFO")

        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            uvicorn_logger = logging.getLogger(name)
            assert len(uvicorn_logger.handlers) > 0
            assert any(
                isinstance(h.formatter, JsonFormatter)
                for h in uvicorn_logger.handlers
            )

    def test_no_duplicate_handlers_on_reconfigure(self):
        """Calling configure_logging twice should not duplicate handlers."""
        configure_logging(level="INFO")
        root = logging.getLogger()
        handler_count = len(root.handlers)

        configure_logging(level="INFO")
        assert len(root.handlers) == handler_count
