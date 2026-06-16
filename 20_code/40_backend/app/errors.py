"""
@module: app.errors
@context: FastAPI backend — cross-cutting concern.
@role: Central application error type and exception handler, so failures are
       reported as a uniform JSON envelope instead of ad-hoc handling scattered
       across modules (project_rules.md §4). Register via
       register_error_handlers(app).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Base class for expected application errors.

    Carries an HTTP status and a short machine-readable ``code`` so the API can
    return a consistent error envelope. Raise subclasses for specific cases.
    """

    status_code: int = 400
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


def register_error_handlers(app: FastAPI) -> None:
    """Attach the application's exception handlers to ``app``."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError [%s]: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
