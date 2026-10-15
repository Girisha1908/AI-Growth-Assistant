"""JSON structured logging with a per-request id.

Every line is one JSON object, e.g.
  {"ts":"...","level":"INFO","logger":"retrieval","event":"retrieval","request_id":"ab12..","ms":41,...}
`docker compose logs api | jq` is therefore enough to follow one request across
retrieval, the model call and the database.
"""

import contextvars
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                data[key] = value
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").disabled = True  # we log requests ourselves


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestLogMiddleware:
    """Pure ASGI middleware: assigns a request id, times the request, logs it."""

    def __init__(self, app):
        self.app = app
        self.log = get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid = uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            self.log.info(
                "request",
                extra={"method": scope["method"], "path": scope["path"],
                       "status": status_holder["code"],
                       "ms": round((time.perf_counter() - start) * 1000)},
            )
            request_id_var.reset(token)
