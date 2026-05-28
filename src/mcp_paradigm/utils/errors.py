"""Typed exceptions for Paradigm API errors.

The exception message is what MCP clients surface to the agent. We
build it carefully so the agent can course-correct without a second
round-trip: HTTP status + method + path + Paradigm's structured error
body + a recovery hint specific to the error class.

Paradigm's typical error body shape:

    {
      "code": 400,
      "error": "validation_failed",
      "message": "Quantity must be positive.",
      "data": {"quantity": ["Must be positive."]}
    }

We surface every populated field. If the body is anything else (string,
list, None) we include a truncated repr.
"""

from __future__ import annotations

from typing import Any

_BODY_PREVIEW_MAX = 1000  # chars before truncation in the message


class ParadigmAPIError(Exception):
    """Base class for Paradigm API errors.

    Carries the HTTP status, the request method/path that triggered it,
    the parsed response body, and any request id from the response
    headers. The string form is structured for agent consumption.
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        *,
        method: str | None = None,
        path: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.method = method
        self.path = path
        self.request_id = request_id
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts: list[str] = [f"Paradigm API {self.status_code}"]
        if self.method and self.path:
            parts.append(f"on {self.method} {self.path}")

        # Extract structured fields from a dict body in a stable order.
        body_summary = self._summarize_body()
        if body_summary:
            parts.append(body_summary)

        if self.request_id:
            parts.append(f"request_id={self.request_id}")

        hint = self._hint()
        if hint:
            parts.append(f"hint: {hint}")

        return " | ".join(parts)

    def _summarize_body(self) -> str:
        body = self.body
        if body is None or body == "":
            return ""
        if isinstance(body, dict):
            fields: list[str] = []
            for key in ("error", "code", "message", "detail"):
                value = body.get(key)
                if value not in (None, ""):
                    fields.append(f"{key}={value!r}")
            # `data` is typically a per-field validation map; render compactly.
            data = body.get("data")
            if data:
                rendered = _truncate(repr(data), _BODY_PREVIEW_MAX)
                fields.append(f"data={rendered}")
            # Any other keys we haven't surfaced explicitly.
            extra = {
                k: v
                for k, v in body.items()
                if k not in {"error", "code", "message", "detail", "data"}
            }
            if extra:
                fields.append(f"other={_truncate(repr(extra), _BODY_PREVIEW_MAX)}")
            if fields:
                return " ".join(fields)
            # Fallback: stringify the whole dict (truncated).
            return f"body={_truncate(repr(body), _BODY_PREVIEW_MAX)}"
        # Non-dict body (string, list, etc.) — repr and truncate.
        return f"body={_truncate(repr(body), _BODY_PREVIEW_MAX)}"

    def _hint(self) -> str | None:
        """Override in subclasses to attach a recovery hint."""
        return None

    def to_dict(self) -> dict[str, Any]:
        """Structured form for tools that want to surface errors as data
        (e.g. ``paradigm_desk_overview`` composites) rather than raise."""
        return {
            "error_type": type(self).__name__,
            "status_code": self.status_code,
            "method": self.method,
            "path": self.path,
            "request_id": self.request_id,
            "body": self.body,
            "message": str(self),
            "hint": self._hint(),
        }


class ParadigmAuthError(ParadigmAPIError):
    """401 / 403 — bad bearer, bad signature, or expired credentials."""

    def _hint(self) -> str:
        return (
            "Verify PARADIGM_ACCESS_KEY and PARADIGM_SIGNING_KEY are set "
            "and refer to the same key pair. PARADIGM_SIGNING_KEY must be "
            "the base64-encoded HMAC key issued by Paradigm (NOT the hex "
            "form). Confirm PARADIGM_ENVIRONMENT matches the key's "
            "environment (prod vs testnet). Run paradigm_echo to verify "
            "signing end-to-end."
        )


class ParadigmNotFoundError(ParadigmAPIError):
    """404 — resource id doesn't exist or isn't visible to the desk."""

    def _hint(self) -> str:
        return (
            "Verify the id exists and is visible to this desk. RFQs and "
            "OBs expire; orders/quotes close after fill or cancel. List "
            "the resource first (e.g. paradigm_drfqv2_rfqs or "
            "paradigm_obv1_obs) to confirm the id is currently active."
        )


class ParadigmValidationError(ParadigmAPIError):
    """400 / 422 — request body or query parameters rejected by the API."""

    def _hint(self) -> str:
        return (
            "Inspect the `data` field above for per-field error messages. "
            "Common causes: missing required field, wrong type (e.g. "
            "passing a number where a decimal string is expected), value "
            "outside venue limits (min_block_size, min_tick_size), or "
            "post-only price that crosses the book."
        )


class ParadigmRateLimitedError(ParadigmAPIError):
    """429 — rate-limited, or Market Maker Protection has fired."""

    def _hint(self) -> str:
        return (
            "Back off and retry with exponential delay. If MMP fired, the "
            "desk is paused — call paradigm_drfqv2_mmp / paradigm_obv1_mmp "
            "/ paradigm_fspd_mmp with action='status' to check, and "
            "action='reset' to re-arm after investigation."
        )


class ParadigmServerError(ParadigmAPIError):
    """5xx — server-side failure."""

    def _hint(self) -> str:
        return (
            "Paradigm-side failure. Idempotent GETs are safe to retry "
            "with backoff. Do NOT auto-retry POST/PUT/PATCH (order-placing "
            "calls) — surface to the user; the order may or may not have "
            "landed and a retry could double-fill."
        )


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"…(+{len(s) - limit} chars)"


def raise_for_status(
    status_code: int,
    body: Any,
    *,
    method: str | None = None,
    path: str | None = None,
    request_id: str | None = None,
) -> None:
    """Map an HTTP status to the typed exception, or no-op on 2xx."""
    if 200 <= status_code < 300:
        return
    kwargs = {"method": method, "path": path, "request_id": request_id}
    if status_code in (401, 403):
        raise ParadigmAuthError(status_code, body, **kwargs)
    if status_code == 404:
        raise ParadigmNotFoundError(status_code, body, **kwargs)
    if status_code in (400, 422):
        raise ParadigmValidationError(status_code, body, **kwargs)
    if status_code == 429:
        raise ParadigmRateLimitedError(status_code, body, **kwargs)
    if 500 <= status_code < 600:
        raise ParadigmServerError(status_code, body, **kwargs)
    raise ParadigmAPIError(status_code, body, **kwargs)
