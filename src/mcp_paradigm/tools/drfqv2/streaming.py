"""DRFQv2 WebSocket subscription tools — snapshot + tail interface.

WebSocket events are push, not request/response, so these three tools
sit on top of the process-wide :class:`WSManager`: ``subscribe`` opens a
channel and returns a ``subscription_id``, ``poll`` drains buffered
events since the last cursor, and ``unsubscribe`` closes it. This lets a
quoting agent consume live RFQs, orders, BBOs, and trades without REST
polling — call ``poll`` in a tight loop instead of re-listing over HTTP.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.errors import normalize_rejection
from mcp_paradigm.utils.models import PermissiveModel
from mcp_paradigm.utils.ws_manager import CHANNELS, get_ws_manager

Channel = Literal["rfq", "order", "bbo", "trade", "trade_confirmation", "mmp"]


class Subscription(PermissiveModel):
    """Owned ack returned by ``paradigm_subscribe``."""

    subscription_id: Annotated[
        str, Field(description="Id to pass to paradigm_poll / paradigm_unsubscribe.")
    ]
    channel: Annotated[str, Field(description="The subscribed channel.")]
    cancel_on_disconnect: Annotated[
        bool | None,
        Field(description="Cancel-on-disconnect in effect for the shared socket."),
    ] = None


class PollResult(PermissiveModel):
    """Owned envelope returned by ``paradigm_poll``.

    ``events`` holds raw buffered events (each possibly carrying a
    ``rejection`` block); they're passed through as ``Any``.
    """

    subscription_id: Annotated[str, Field(description="The polled subscription id.")]
    channel: Annotated[str, Field(description="The subscription's channel.")]
    events: Annotated[
        list[Any],
        Field(
            default_factory=list,
            description="Buffered events since the last cursor; each carries seq/channel/received_at/data (and a `rejection` block when applicable).",
        ),
    ]
    cursor: Annotated[
        int | None,
        Field(description="Cursor to pass back as `since` (advances automatically)."),
    ] = None
    connected: Annotated[
        bool | None,
        Field(description="False if the socket dropped — re-subscribe to reconnect."),
    ] = None


class Unsubscribed(PermissiveModel):
    """Owned ack returned by ``paradigm_unsubscribe``."""

    subscription_id: Annotated[str, Field(description="The closed subscription id.")]
    channel: Annotated[str, Field(description="The channel that was closed.")]
    closed: Annotated[bool | None, Field(description="Always true on success.")] = None


# Channels whose events can carry a rejection we want to surface as a
# structured block (Paradigm has no dedicated error channel — rejections
# arrive as state transitions on these streams).
_REJECTION_CHANNELS = frozenset({"trade", "order"})


def _annotate_rejection(event: dict[str, Any]) -> dict[str, Any]:
    """Attach a structured ``rejection`` block to a rejected push event.

    Mirrors the REST path so a pushed rejection is as legible as a polled
    one. Non-rejection events pass through unchanged.
    """
    if event.get("channel") not in _REJECTION_CHANNELS:
        return event
    rejection = normalize_rejection(event.get("data"))
    if rejection is None:
        return event
    return {**event, "rejection": rejection}


@server.tool(
    name="paradigm_subscribe",
    title="Subscribe (WebSocket)",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=False),
)
async def paradigm_subscribe(
    channel: Annotated[
        Channel,
        Field(description=f"Stream to open. One of: {', '.join(CHANNELS)}."),
    ],
    cancel_on_disconnect: Annotated[
        bool,
        Field(
            description=(
                "Connection-level Paradigm setting. If true, the platform "
                "cancels the desk's live orders when this socket drops. "
                "Only applies on the subscribe that first opens the "
                "connection; leave false for read-only consumers."
            )
        ),
    ] = False,
) -> Subscription:
    """Open a DRFQv2 WebSocket subscription and return its ``subscription_id``.

    The server holds one shared WebSocket connection and keeps the events
    buffered; pass the returned ``subscription_id`` to ``paradigm_poll``
    to drain them and to ``paradigm_unsubscribe`` to close. Polling starts
    from the moment of subscription — events that arrived earlier are not
    replayed.
    """
    manager = await get_ws_manager()
    return await manager.subscribe(channel, cancel_on_disconnect=cancel_on_disconnect)


@server.tool(
    name="paradigm_poll",
    title="Poll Subscription (WebSocket)",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=False),
)
async def paradigm_poll(
    subscription_id: Annotated[str, Field(description="Id returned by paradigm_subscribe.")],
    since: Annotated[
        int | None,
        Field(
            description=(
                "Return only events with seq greater than this cursor. "
                "Omit to continue from the last poll's cursor."
            )
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Field(description="Max events to return this poll.", ge=1, le=10000),
    ] = None,
) -> PollResult:
    """Drain buffered events for a subscription.

    Returns ``{events, cursor, channel, connected}``. Each event carries a
    monotonic ``seq``, the ``channel``, ``received_at``, and the ``data``
    payload. Pass the returned ``cursor`` back as ``since`` (or just call
    again — the cursor advances automatically) to get only new events.
    Events age out of the buffer after the configured TTL, so poll often
    enough to keep up.

    Rejections are pushed, not polled: Paradigm has no dedicated error
    channel, so a rejected trade/order arrives as a state transition on
    the ``trade``/``order`` channel. Such events are annotated with a
    structured ``rejection`` block (``reason``/``code``/``message``/
    ``timestamp``) so a failure reads as a failure rather than "still
    waiting".
    """
    manager = await get_ws_manager()
    result = await manager.poll(subscription_id, since=since, limit=limit)
    events = result.get("events")
    if isinstance(events, list):
        result["events"] = [_annotate_rejection(e) for e in events]
    return result


@server.tool(
    name="paradigm_unsubscribe",
    title="Unsubscribe (WebSocket)",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_unsubscribe(
    subscription_id: Annotated[str, Field(description="Id returned by paradigm_subscribe.")],
) -> Unsubscribed:
    """Close a DRFQv2 WebSocket subscription.

    When the last subscription closes, the shared WebSocket connection is
    torn down.
    """
    manager = await get_ws_manager()
    return await manager.unsubscribe(subscription_id)
