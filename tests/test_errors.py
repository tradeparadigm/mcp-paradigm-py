"""Tests for the agent-facing error formatting.

Tools surface exceptions to MCP clients via ``str(exc)`` — the format
the agent reads is what matters here. These tests pin the shape so we
don't accidentally lose context (status code, method, path, body fields,
recovery hint) in a future refactor.
"""

from __future__ import annotations

import pytest

from mcp_paradigm.utils.errors import (
    ParadigmAPIError,
    ParadigmAuthError,
    ParadigmNotFoundError,
    ParadigmRateLimitedError,
    ParadigmServerError,
    ParadigmValidationError,
    raise_for_status,
)


def test_message_includes_status_method_path() -> None:
    exc = ParadigmAPIError(500, {"error": "boom"}, method="GET", path="/v2/drfq/echo/")
    msg = str(exc)
    assert msg.startswith("500 GET /v2/drfq/echo/")
    assert "boom" in msg


def test_message_includes_request_id_when_present() -> None:
    exc = ParadigmAPIError(500, {}, method="GET", path="/v2/drfq/echo/", request_id="req-abc-123")
    assert "request_id=req-abc-123" in str(exc)


def test_validation_error_extracts_data_field() -> None:
    body = {
        "code": 422,
        "error": "validation_failed",
        "message": "Invalid input.",
        "data": {"quantity": ["This field is required."]},
    }
    exc = ParadigmValidationError(422, body, method="POST", path="/v2/drfq/orders/")
    msg = str(exc)
    assert msg.startswith("422 POST /v2/drfq/orders/")
    assert "validation_failed: Invalid input." in msg
    assert "quantity" in msg
    assert "required" in msg
    # `code` should be dropped when it matches the HTTP status.
    assert "code=" not in msg
    assert "hint:" in msg


def test_message_is_concise() -> None:
    """One-line, compact, no redundant labels."""
    exc = ParadigmValidationError(
        422,
        {"error": "validation_failed", "message": "Quantity must be positive."},
        method="POST",
        path="/v2/drfq/orders/",
    )
    msg = str(exc)
    # Expected shape (illustrative): "422 POST /v2/drfq/orders/ | validation_failed: Quantity must be positive. | hint: ..."
    assert msg.count("|") <= 3
    assert "Paradigm API" not in msg  # no chatty prefix


def test_auth_error_has_recovery_hint() -> None:
    exc = ParadigmAuthError(401, {"detail": "Invalid signature"})
    msg = str(exc)
    assert msg.startswith("401")
    assert "PARADIGM_ACCESS_KEY" in msg
    assert "PARADIGM_SIGNING_KEY" in msg
    assert "paradigm_echo" in msg


def test_not_found_hint_suggests_listing() -> None:
    exc = ParadigmNotFoundError(404, None, method="GET", path="/v2/drfq/rfqs/999/")
    msg = str(exc)
    assert msg.startswith("404")
    assert "paradigm_drfqv2_rfqs" in msg


def test_rate_limited_hint_mentions_mmp_and_backoff() -> None:
    exc = ParadigmRateLimitedError(429, {"error": "rate_limit"})
    msg = str(exc)
    assert msg.startswith("429")
    assert "MMP" in msg
    assert "back off" in msg.lower()


def test_server_error_hint_warns_against_auto_retry_of_writes() -> None:
    exc = ParadigmServerError(503, None)
    msg = str(exc)
    assert msg.startswith("503")
    assert "POST" in msg
    assert "double-fill" in msg


def test_to_dict_round_trips_all_fields() -> None:
    exc = ParadigmValidationError(
        422,
        {"data": {"x": ["bad"]}},
        method="POST",
        path="/v2/drfq/orders/",
        request_id="r-1",
    )
    d = exc.to_dict()
    assert d["error_type"] == "ParadigmValidationError"
    assert d["status_code"] == 422
    assert d["method"] == "POST"
    assert d["path"] == "/v2/drfq/orders/"
    assert d["request_id"] == "r-1"
    assert d["body"] == {"data": {"x": ["bad"]}}
    assert "hint" in d
    assert d["hint"] is not None
    assert d["message"] == str(exc)


def test_raise_for_status_maps_codes_and_passes_context() -> None:
    cases = [
        (401, ParadigmAuthError),
        (403, ParadigmAuthError),
        (404, ParadigmNotFoundError),
        (400, ParadigmValidationError),
        (422, ParadigmValidationError),
        (429, ParadigmRateLimitedError),
        (500, ParadigmServerError),
        (599, ParadigmServerError),
        (418, ParadigmAPIError),
    ]
    for status, cls in cases:
        with pytest.raises(cls) as info:
            raise_for_status(status, {"error": "x"}, method="GET", path="/p", request_id="rid")
        assert info.value.status_code == status
        assert info.value.method == "GET"
        assert info.value.path == "/p"
        assert info.value.request_id == "rid"


def test_raise_for_status_noop_on_2xx() -> None:
    for status in (200, 201, 204, 207, 299):
        raise_for_status(status, None)  # should not raise


def test_long_body_truncated_in_message() -> None:
    body = {"data": {"k": "x" * 5000}}
    exc = ParadigmValidationError(422, body)
    msg = str(exc)
    # The truncation marker should appear somewhere.
    assert "…(+" in msg
    # Sanity: message should be reasonably bounded.
    assert len(msg) < 6000
