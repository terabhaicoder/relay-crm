import json
import logging
from datetime import UTC, datetime


class SafeJSONFormatter(logging.Formatter):
    """Emit allowlisted operational metadata; never serialize arbitrary extra or exceptions.

    Only fixed event codes belong in `safe_event`. Request bodies, URLs, query strings,
    SQL parameters, exception text and arbitrary library messages are intentionally omitted.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "safe_event", "library_event"),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # Uvicorn access messages include request URLs, which may contain personal data.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
