import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=ErrorBody(code=code, message=message)).model_dump(),
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        messages = {
            401: ("UNAUTHENTICATED", "Please sign in to continue."),
            403: ("FORBIDDEN", "You do not have permission to do this."),
            404: ("NOT_FOUND", "The requested record was not found."),
            405: ("METHOD_NOT_ALLOWED", "This action is not available."),
            409: ("CONFLICT", "This record conflicts with an existing record."),
            413: ("REQUEST_TOO_LARGE", "The request is too large."),
            422: ("VALIDATION_ERROR", "Please check your details."),
            429: ("RATE_LIMITED", "Too many requests. Please try again shortly."),
        }
        code, message = messages.get(exc.status_code, ("REQUEST_FAILED", "Request failed."))
        if exc.status_code < 500 and isinstance(exc.detail, str) and exc.status_code != 404:
            message = exc.detail
        if exc.status_code < 500 and isinstance(exc.detail, dict):
            safe_message = exc.detail.get("message")
            fields = exc.detail.get("fields")
            if isinstance(safe_message, str):
                message = safe_message
            details = {"fields": fields} if isinstance(fields, list) else {}
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error=ErrorBody(code=code, message=message, details=details)
                ).model_dump(),
            )
        response = error_response(exc.status_code, code, message)
        for name, value in (exc.headers or {}).items():
            if name.lower() in {"retry-after", "www-authenticate"}:
                response.headers[name] = value
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo request values (e.g. tokens or salary) in validation failures.
        fields = [{"field": ".".join(map(str, e["loc"])), "code": e["type"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorBody(
                    code="VALIDATION_ERROR",
                    message="Please check the highlighted fields.",
                    details={"fields": fields},
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("request_failed", extra={"safe_event": "request_failed"})
        return error_response(500, "INTERNAL_ERROR", "Something went wrong. Please try again.")
