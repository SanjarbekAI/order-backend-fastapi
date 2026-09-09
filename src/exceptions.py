"""Shared domain-error hierarchy and the FastAPI handlers that render it.

Domain code (services, repositories) raises :class:`DomainError` subclasses and
never imports ``fastapi``. A single set of exception handlers, registered in
``src.main``, turns those into consistent JSON responses:

    {"error": {"code": "order_not_found", "message": "Order 42 not found"}}
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for expected, business-level failures.

    Subclasses set ``status_code`` and ``code``; the human-readable message is
    passed per-instance so it can carry identifiers.
    """

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotAuthenticated(DomainError):
    status_code = 401
    code = "not_authenticated"

    def __init__(self, message: str = "Missing or invalid authentication credentials"):
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )
