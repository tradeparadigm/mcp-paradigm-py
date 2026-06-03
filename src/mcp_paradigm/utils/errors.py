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

from datetime import UTC, datetime
from typing import Any

from mcp_paradigm.utils.models import Rejection

_BODY_PREVIEW_MAX = 1000  # chars before truncation in the message


def _utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a trailing ``Z``."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
        self.timestamp = _utc_now_iso()
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        head = str(self.status_code)
        if self.method and self.path:
            head = f"{head} {self.method} {self.path}"
        parts: list[str] = [head]

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
        if body is None or body == "" or body == {} or body == []:
            return ""
        if not isinstance(body, dict):
            return _truncate(repr(body), _BODY_PREVIEW_MAX)
        head = self._summarize_dict_head(body)
        tail = self._summarize_dict_tail(body)
        if head and tail:
            return f"{head} ({tail})"
        return head or tail or _truncate(repr(body), _BODY_PREVIEW_MAX)

    def _summarize_dict_head(self, body: dict[str, Any]) -> str:
        """Compact `error: message: detail` (and `code=...` if not redundant)."""
        parts: list[str] = []
        seen: set[str] = set()
        for key in ("error", "message", "detail"):
            value = body.get(key)
            if value in (None, ""):
                continue
            text = str(value)
            if text in seen:
                continue  # don't repeat the same string under two keys
            seen.add(text)
            parts.append(text)
        code = body.get("code")
        if code and code != self.status_code:
            parts.append(f"code={code}")
        return ": ".join(parts)

    def _summarize_dict_tail(self, body: dict[str, Any]) -> str:
        """Validation `data` map and any unrecognized keys."""
        parts: list[str] = []
        data = body.get("data")
        if data:
            parts.append(f"data={_truncate(repr(data), _BODY_PREVIEW_MAX)}")
        extra = {
            k: v for k, v in body.items() if k not in {"error", "code", "message", "detail", "data"}
        }
        if extra:
            parts.append(f"extra={_truncate(repr(extra), _BODY_PREVIEW_MAX)}")
        return ", ".join(parts)

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
            "timestamp": self.timestamp,
            "body": self.body,
            "message": str(self),
            "hint": self._hint(),
        }


class ParadigmAuthError(ParadigmAPIError):
    """401 / 403 — bad bearer, bad signature, or expired credentials."""

    def _hint(self) -> str:
        return (
            "Check PARADIGM_ACCESS_KEY + PARADIGM_SIGNING_KEY (base64) "
            "and PARADIGM_ENVIRONMENT; call paradigm_echo to verify."
        )


class ParadigmNotFoundError(ParadigmAPIError):
    """404 — resource id doesn't exist or isn't visible to the desk."""

    def _hint(self) -> str:
        return "List the parent (e.g. paradigm_drfqv2_rfqs) — id may be expired or not yours."


class ParadigmValidationError(ParadigmAPIError):
    """400 / 422 — request body or query parameters rejected by the API."""

    def _hint(self) -> str:
        return "Read `data` for per-field errors; prices/quantities must be decimal strings."


class ParadigmRateLimitedError(ParadigmAPIError):
    """429 — rate-limited, or Market Maker Protection has fired."""

    def _hint(self) -> str:
        return "Back off exponentially. If MMP fired, call paradigm_*_mmp(action='status')."


class ParadigmServerError(ParadigmAPIError):
    """5xx — server-side failure."""

    def _hint(self) -> str:
        return "Retry GETs with backoff. Do NOT auto-retry POST/PUT/PATCH (double-fill risk)."


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"…(+{len(s) - limit} chars)"


# Body keys that, by convention, carry a rejection reason code/enum.
_REJECTION_REASON_KEYS = ("rejection_reason", "reject_reason", "reason", "error")
# Body keys carrying a human-readable rejection message.
_REJECTION_MESSAGE_KEYS = ("message", "detail", "rejection_message")
# Body keys carrying a numeric/string rejection code.
_REJECTION_CODE_KEYS = ("code", "reason_code", "error_code")


def _first_present(body: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-empty value among ``keys`` in ``body``."""
    for key in keys:
        value = body.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_rejection(body: Any, meta: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Structured rejection block for a 2xx body that signals a rejection.

    Business-level rejections (a trade/order/RFQ that comes back
    ``REJECTED``) arrive as ordinary 2xx responses, so the typed
    ``ParadigmAPIError`` path never fires and the agent only sees a coarse
    state enum — which is exactly why a failure "looks like still
    waiting". This pulls the reason/code/message out of the body (across
    the field names Paradigm uses) and stamps it with the request id +
    timestamp from ``meta`` so the caller learns *why* in one shot.

    Returns ``None`` when the body shows no sign of rejection, so callers
    can attach the block conditionally without changing success payloads.
    """
    if not isinstance(body, dict):
        return None

    state = body.get("state") or body.get("status")
    state_rejected = isinstance(state, str) and state.upper() == "REJECTED"

    reason = _first_present(body, _REJECTION_REASON_KEYS)
    message = _first_present(body, _REJECTION_MESSAGE_KEYS)
    code = _first_present(body, _REJECTION_CODE_KEYS)

    # Only treat the body as a rejection if it actually says so — either a
    # REJECTED state, or an explicit reason/error field. A bare PENDING
    # order with no error must pass through untouched.
    if not state_rejected and reason is None:
        return None

    block = Rejection(
        code=code,
        reason=reason if reason is not None else (state if state_rejected else None),
        message=message,
        request_id=(meta or {}).get("request_id"),
        timestamp=(meta or {}).get("timestamp") or _utc_now_iso(),
    )
    return block.model_dump()


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
