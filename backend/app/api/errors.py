"""Domain exceptions + FastAPI handlers that emit the standard error envelope."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.envelope import error
from app.core.logging import get_logger

log = get_logger("api.errors")


class AppError(Exception):
    code = "APP_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, details: object = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error("VALIDATION_ERROR", "Request validation failed", exc.errors()),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):  # pragma: no cover
        log.error("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error("INTERNAL_ERROR", "An unexpected error occurred"),
        )
