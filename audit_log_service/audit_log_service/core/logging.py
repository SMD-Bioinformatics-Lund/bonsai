"""For configuring logging"""

import json
import logging
import datetime as dt
import sys
import traceback
from typing import Any
from bson import ObjectId

from .config import Settings
from audit_log_service.version import __version__ as version


class _SafeJSONEncoder(json.JSONEncoder):
    """Safe JSON encoder that serialze mongodb ObjectIds to a timestamp."""

    def default(self, o: Any) -> Any:
        """Default serializer."""

        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, dt.datetime):
            return o.astimezone(dt.timezone.utc).isoformat()
        return str(o)


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production."""

    def __init__(self, *, include_debug_fields: bool = False):
        super().__init__()
        self.include_debug_fields = include_debug_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record in JSON format."""
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()

        # Base fields
        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", None)
            "version": version,
        }

        # Additional fields can be enabled for debugging
        if self.include_debug_fields or record.levelno >= logging.DEBUG:
            payload.update(
                {
                    "module": record.module,
                    "funcName": record.funcName,
                    "lineNo": record.lineno,
                    "process": record.process,
                    "thread": record.thread,
                }
            )

        # Merge any "extra" fields passed via `extra={...}`
        # (skip standard LogRecord attributes to avoid duplication)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in payload:
                payload[key] = value

        # Exceptions
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            payload["exception"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": str(exc_value),
                "stacktrace": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            }

        return json.dumps(payload, cls=_SafeJSONEncoder, ensure_ascii=False)

class ConsoleFormatter(logging.Formatter):
    """Human friendly formatter for local development."""

    COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",   # Cyan
        "INFO": "\033[32m",    # Green
        "WARNING": "\033[33m", # Yellow
        "ERROR": "\033[31m",   # Red
        "CRITICAL": "\033[35m" # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, *, use_color: bool = True):
        super().__init__()
        self.use_color = use_color and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        ts = dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S")
        lvl = record.levelname
        color = self.COLORS.get(lvl, "") if self.use_color else ""
        reset = self.RESET if self.use_color else ""
        service = getattr(record, "service", None)
        env = getattr(record, "env", None)

        prefix = f"{ts} {color}{lvl:8}{reset} [{service or record.name}]"
        if env:
            prefix += f"({env})"

        msg = record.getMessage()
        out = f"{prefix} - {msg}"

        if record.exc_info:
            out += "\n" + "".join(traceback.format_exception(*record.exc_info))
        return out


def configure_logging(settings: Settings, service_name: str | None = None, json_logs: bool | None = None):
    """Initialize root and uvicorn loggers with consistent formatting.
    
    Parameters can be provided via:
      - `settings` object with attributes: LOG_LEVEL, APP_ENV, SERVICE_NAME, SERVICE_VERSION, LOG_FORMAT
      - explicit kwargs (override settings)
    """
    service_name = (service_name or settings.service_name)
    log_level = settings.log_level

    # build handler with formatters and filter
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)

    if json_logs is None:
        json_logs = settings.log_format == "json"
    if json_logs:
        handler.setFormatter(JSONFormatter(include_debug_fields=(log_level == "DEBUG")))
    else:
        handler.setFormatter(ConsoleFormatter(use_color=True))

    # Root logger
    root = logging.getLogger()
    # Clear existing handlers to avoid duplicates
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(log_level)
    root.addHandler(handler)
    logging.captureWarnings(True)

    # Make uvicorn loggers propagate to root
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = []  # let them propagate to root
        log.propagate = True
        log.setLevel(log_level)
