"""Permissive Pydantic models for the response envelopes the server *owns*.

These model only the shapes the server constructs itself — pagination
envelopes, the rejection block, streaming acks — never the raw upstream
Paradigm objects (RFQs, orders, trades, desks), which stay passthrough so
an upstream field change can never turn a usable 200 into a validation
failure.

All models are permissive (``extra="allow"``) and keep their nested
payload fields typed as ``Any``, so:

- FastMCP derives an ``outputSchema`` from the return annotation and emits
  structured content (it validates the returned dict against the model);
- embedded upstream sub-objects (a desk dict, a trade dict) flow through
  untouched; and
- a new field the server starts returning is preserved rather than dropped.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class PermissiveModel(BaseModel):
    """Base for owned envelopes: keep unknown keys instead of dropping them."""

    model_config = ConfigDict(extra="allow")


class Rejection(PermissiveModel):
    """Structured reason a 2xx RFQ/order/trade was rejected.

    Single source of truth for the block ``errors.normalize_rejection``
    builds and the REST write tools / WS poll / trades enrichment attach.
    """

    reason: Annotated[
        Any,
        Field(description="Rejection reason code/enum (the REJECTED state or an upstream error)."),
    ] = None
    code: Annotated[
        Any, Field(description="Numeric or string rejection code, when the API provides one.")
    ] = None
    message: Annotated[Any, Field(description="Human-readable rejection message, if any.")] = None
    request_id: Annotated[
        str | None,
        Field(
            description="Paradigm request id from the response headers, for support correlation."
        ),
    ] = None
    timestamp: Annotated[
        str | None, Field(description="UTC ISO-8601 time the rejection was observed.")
    ] = None
