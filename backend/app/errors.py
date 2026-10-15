"""Structured errors. Every failure leaves the API as

    {"error": {"code": "...", "message": "...", "hint": "..."}}

so the frontend (and an evaluator with curl) never has to parse free text.
"""

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_utils import get_logger

log = get_logger("errors")


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, hint: Optional[str] = None):
        super().__init__(message)
        self.code, self.message, self.status, self.hint = code, message, status, hint


class ProviderError(AppError):
    """The LLM provider failed (down, timed out, misconfigured)."""


def provider_error_from(exc: Exception) -> ProviderError:
    """Map low-level exceptions to a friendly, actionable error."""
    if isinstance(exc, ValueError):  # e.g. missing API key
        return ProviderError("provider_not_configured", str(exc), 400,
                             "Set the key in .env (see .env.example) or switch provider.")
    if isinstance(exc, TimeoutError):
        return ProviderError("provider_timeout", str(exc), 504,
                             "The model took too long. Try a shorter request or a smaller model.")
    if isinstance(exc, ConnectionError):
        return ProviderError("provider_unavailable", str(exc), 503,
                             "Is Ollama running? Start it, or switch provider in the composer.")
    return ProviderError("provider_error", str(exc), 502, "See API logs (event=llm_call).")


def _body(code: str, message: str, hint: Optional[str] = None) -> dict:
    err = {"code": code, "message": message}
    if hint:
        err["hint"] = hint
    return {"error": err}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        log.warning("app_error", extra={"code": exc.code, "message_text": exc.message})
        return JSONResponse(_body(exc.code, exc.message, exc.hint), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(f"http_{exc.status_code}", str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return JSONResponse(
            _body("validation_error", f"{loc}: {first.get('msg', 'invalid request')}"),
            status_code=422,
        )

    @app.exception_handler(OperationalError)
    async def _db_error(_: Request, exc: OperationalError):
        log.error("database_unavailable", extra={"error": str(exc.orig)[:200]})
        return JSONResponse(_body("database_unavailable", "The database is not reachable.",
                                  "Check `docker compose ps` and the db container logs."),
                            status_code=503)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled_exception")
        return JSONResponse(_body("internal_error", "Unexpected server error.",
                                  "Check API logs using the request id."), status_code=500)
