"""Typed exceptions for Paradigm API errors."""

from typing import Any


class ParadigmAPIError(Exception):
    """Base class for Paradigm API errors."""

    def __init__(self, status_code: int, body: Any, message: str | None = None) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message or f"Paradigm API error {status_code}: {body}")


class ParadigmAuthError(ParadigmAPIError):
    """401/403 — bad bearer or signature."""


class ParadigmNotFoundError(ParadigmAPIError):
    """404."""


class ParadigmValidationError(ParadigmAPIError):
    """400 — body or query validation failed."""


class ParadigmRateLimitedError(ParadigmAPIError):
    """429."""


class ParadigmServerError(ParadigmAPIError):
    """5xx."""


def raise_for_status(status_code: int, body: Any) -> None:
    """Map an HTTP status to the typed exception, or no-op on 2xx."""
    if 200 <= status_code < 300:
        return
    if status_code in (401, 403):
        raise ParadigmAuthError(status_code, body)
    if status_code == 404:
        raise ParadigmNotFoundError(status_code, body)
    if status_code in (400, 422):
        raise ParadigmValidationError(status_code, body)
    if status_code == 429:
        raise ParadigmRateLimitedError(status_code, body)
    if 500 <= status_code < 600:
        raise ParadigmServerError(status_code, body)
    raise ParadigmAPIError(status_code, body)
