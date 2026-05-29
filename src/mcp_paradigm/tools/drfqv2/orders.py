"""DRFQv2 order lifecycle + unified DRFQv2 cancel.

Single-fetch is via ``paradigm_drfqv2_orders(order_id=...)``. Posting and
amending share one tool: pass ``order_id`` to PUT (amend); omit to POST.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
OrderState = Literal["OPEN", "CLOSED", "PENDING"]
Side = Literal["BUY", "SELL"]
OrderType = Literal["LIMIT", "HIDDEN"]
TimeInForce = Literal["FILL_OR_KILL", "GOOD_TILL_CANCELED"]
Currency = Literal["AVAX", "BCH", "BTC", "ETH", "SOL", "TONCOIN", "TRX", "USD", "USDC", "XRP"]


class OrderLeg(BaseModel):
    instrument_id: int = Field(description="Paradigm instrument id.")
    price: str = Field(description="Leg price (decimal string).")


@server.tool(
    name="paradigm_drfqv2_orders",
    title="DRFQv2 Orders",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_orders(
    order_id: Annotated[
        str | None,
        Field(description="If set, fetches the single order; otherwise list with filters."),
    ] = None,
    rfq_id: Annotated[str | None, Field(description="Filter by RFQ id.")] = None,
    state: Annotated[OrderState | None, Field(description="Filter by state.")] = None,
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    currency: Annotated[Currency | None, Field(description="Quote currency filter.")] = None,
    base_currency: Annotated[Currency | None, Field(description="Base currency filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List the desk's DRFQv2 orders, or fetch one by id."""
    client = await get_paradigm_client()
    if order_id is not None:
        return await client.get(f"/v2/drfq/orders/{order_id}/")
    return await client.get(
        "/v2/drfq/orders/",
        rfq_id=rfq_id,
        state=state,
        venue=venue,
        currency=currency,
        base_currency=base_currency,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_drfqv2_post_order",
    title="DRFQv2 Post / Update Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_drfqv2_post_order(
    rfq_id: Annotated[str, Field(description="The RFQ to quote/cross.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    quantity: Annotated[str, Field(description="Order quantity (decimal string).")],
    type: Annotated[OrderType, Field(description="LIMIT or HIDDEN.")] = "LIMIT",
    time_in_force: Annotated[
        TimeInForce,
        Field(description="Maker quoting = GOOD_TILL_CANCELED; taker crossing = FILL_OR_KILL."),
    ] = "GOOD_TILL_CANCELED",
    price: Annotated[
        str | None, Field(description="Order price (decimal). Required for LIMIT.")
    ] = None,
    legs: Annotated[
        list[OrderLeg] | None,
        Field(description="Per-leg prices for multi-leg structures."),
    ] = None,
    account_name: Annotated[
        str | None, Field(description="Account name (omit for desk default).", max_length=256)
    ] = None,
    label: Annotated[
        str | None, Field(description="Caller idempotency label.", max_length=128)
    ] = None,
    order_id: Annotated[
        str | None,
        Field(description="If set, amends an existing order (PUT) instead of posting new (POST)."),
    ] = None,
) -> Any:
    """Post a new order, or amend an existing one if ``order_id`` is set.

    Async-first: the response state is always ``PENDING`` with zeroed
    fill quantities. Poll via ``paradigm_drfqv2_orders(order_id=...)``
    or subscribe to the ``order`` channel for terminal state.
    Destructive — puts money on the wire.
    """
    client = await get_paradigm_client()
    body: dict[str, Any] = {
        "rfq_id": rfq_id,
        "side": side,
        "quantity": quantity,
        "type": type,
        "time_in_force": time_in_force,
    }
    if price is not None:
        body["price"] = price
    if legs:
        body["legs"] = [leg.model_dump() for leg in legs]
    if account_name is not None:
        body["account_name"] = account_name
    if label is not None:
        body["label"] = label
    if order_id is not None:
        return await client.put(f"/v2/drfq/orders/{order_id}/", json_body=body)
    return await client.post("/v2/drfq/orders/", json_body=body)


@server.tool(
    name="paradigm_drfqv2_cancel",
    title="DRFQv2 Cancel",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_cancel(
    target: Annotated[
        Literal["rfq", "order", "orders"],
        Field(
            description="'rfq' cancels an RFQ; 'order' cancels by order_id; 'orders' batch-cancels by filter."
        ),
    ],
    rfq_id: Annotated[str | None, Field(description="RFQ id (for 'rfq' / 'orders').")] = None,
    order_id: Annotated[str | None, Field(description="Order id (for 'order').")] = None,
    state: Annotated[OrderState | None, Field(description="Batch filter: state.")] = None,
    venue: Annotated[Venue | None, Field(description="Batch filter: venue.")] = None,
    currency: Annotated[Currency | None, Field(description="Batch filter: currency.")] = None,
    base_currency: Annotated[
        Currency | None, Field(description="Batch filter: base currency.")
    ] = None,
) -> Any:
    """Cancel a DRFQv2 RFQ, a single order, or a batch by filter.

    For a global kill switch across all products, use
    ``paradigm_kill_switch`` instead.
    """
    client = await get_paradigm_client()
    if target == "rfq":
        if not rfq_id:
            raise ValueError("target='rfq' requires rfq_id")
        await client.delete(f"/v2/drfq/rfqs/{rfq_id}/")
        return {"rfq_id": rfq_id, "canceled": True}
    if target == "order":
        if not order_id:
            raise ValueError("target='order' requires order_id")
        await client.delete(f"/v2/drfq/orders/{order_id}/")
        return {"order_id": order_id, "canceled": True}
    return await client.delete(
        "/v2/drfq/orders/",
        rfq_id=rfq_id,
        state=state,
        venue=venue,
        currency=currency,
        base_currency=base_currency,
    )
