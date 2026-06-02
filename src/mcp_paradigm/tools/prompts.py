"""MCP prompt templates — canned workflows for the common DRFQv2 flows.

Prompts are user-invokable guides a client surfaces in a "workflows" menu.
Each returns a short playbook that names the *real* tools to call in order,
so an agent (or a human driving one) can run a multi-step flow without
re-deriving the sequence. They guide; they don't execute — the agent still
calls the tools, and destructive steps still prompt for approval.

Imported by ``tools/__init__`` so the decorators register at startup.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_paradigm.server.server import server


@server.prompt(
    name="quote_rfq",
    title="Quote an RFQ (maker)",
    description="Playbook for pricing and quoting an open DRFQv2 RFQ as a maker.",
)
def quote_rfq(
    rfq_id: Annotated[str, Field(description="The DRFQv2 RFQ id to quote.")],
) -> str:
    """Maker flow: inspect → price → post → confirm."""
    return f"""You are quoting DRFQv2 RFQ {rfq_id} as a maker. Steps:

1. `paradigm_drfqv2_rfq_snapshot(rfq_id="{rfq_id}")` — read the legs, current
   BBO, and existing order book so you know what you're pricing and where the
   market is.
2. `paradigm_drfqv2_price_legs(...)` — compute indicative leg prices for the
   strategy if you need a reference before applying your own edge.
3. `paradigm_drfqv2_post_order(...)` with your price and size to place the
   quote. This is destructive (puts an order on the wire) — confirm with the
   user before sending.
4. `paradigm_drfqv2_rfq_snapshot(rfq_id="{rfq_id}")` again to confirm your
   order is resting and to watch for a cross.

For live updates instead of re-snapshotting, subscribe to the `order` / `bbo`
channels (see the stream_and_tail prompt)."""


@server.prompt(
    name="broadcast_rfq",
    title="Broadcast an RFQ (taker)",
    description="Playbook for broadcasting a DRFQv2 RFQ to all venue-eligible makers.",
)
def broadcast_rfq(
    venue: Annotated[str, Field(description="Settlement venue, e.g. 'PRDX' or 'DBT'.")],
    base_currency: Annotated[
        str | None,
        Field(description="Optional base currency to narrow the instrument search, e.g. 'BTC'."),
    ] = None,
) -> str:
    """Taker flow: (optionally) see eligible LPs → broadcast → watch quotes."""
    ccy = f" base_currency='{base_currency}'" if base_currency else ""
    return f"""You are sending a DRFQv2 RFQ on venue {venue} to the whole street. Steps:

1. (Optional) `paradigm_drfqv2_counterparties(venue="{venue}")` — see exactly
   which LPs can quote {venue}. You don't need to pass these explicitly; it's
   just to know who will receive the broadcast.
2. `paradigm_drfqv2_instruments(venue="{venue}"{ccy})` — find the instrument id(s)
   for the legs you want to trade.
3. `paradigm_drfqv2_create_rfq(venue="{venue}", legs=[...], quantity="...",
   counterparties=[])` — leave `counterparties` empty to broadcast to every
   maker eligible for {venue} (the default path). Destructive — confirm with the
   user before sending.
4. Watch quotes arrive with `paradigm_drfqv2_rfq_snapshot(rfq_id=...)`, or
   subscribe to the `bbo` channel for live updates (see stream_and_tail).
5. When you like a quote, `paradigm_drfqv2_post_order(...)` to cross and trade
   (destructive — confirm)."""


@server.prompt(
    name="stream_and_tail",
    title="Stream a channel (live, no polling)",
    description="Playbook for consuming a live DRFQv2 WebSocket channel via subscribe/poll/unsubscribe.",
)
def stream_and_tail(
    channel: Annotated[
        str,
        Field(description="Channel to stream: rfq, order, bbo, trade, trade_confirmation, or mmp."),
    ] = "rfq",
) -> str:
    """Push-consume a channel instead of REST polling."""
    return f"""You want live {channel} updates without hammering the REST endpoints. Steps:

1. `paradigm_subscribe(channel="{channel}")` — returns a `subscription_id`. The
   server opens one shared, heartbeated WebSocket and buffers events for you.
2. Loop: `paradigm_poll(subscription_id=...)` — returns `events[]` plus a
   `cursor`. The cursor advances automatically, so calling poll again returns
   only new events. Poll often enough that events don't age out of the buffer.
3. `paradigm_unsubscribe(subscription_id=...)` when you're done — the shared
   connection is torn down once the last subscription closes.

This replaces REST polling loops (e.g. repeatedly calling
`paradigm_drfqv2_rfq_snapshot`) and pushes quotes in near-real-time. If `poll`
ever reports `connected: false`, the socket dropped — re-subscribe to reconnect."""
