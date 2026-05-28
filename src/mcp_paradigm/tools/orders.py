"""Order lifecycle tools (maker quote + taker cross)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
OrderState = Literal["OrderState.CLOSED", "OrderState.OPEN", "OrderState.PENDING"]
Side = Literal["BUY", "SELL"]
OrderType = Literal["LIMIT", "HIDDEN"]
TimeInForce = Literal["FILL_OR_KILL", "GOOD_TILL_CANCELED"]
Currency = Literal[
    "AVAX", "BCH", "BTC", "ETH", "SOL", "TONCOIN", "TRX", "USD", "USDC", "XRP"
]


class OrderLeg(BaseModel):
    instrument_id: int = Field(description="Paradigm instrument id.")
    price: str = Field(description="Leg price (decimal string).")


@server.tool(
    name="paradigm_orders",
    title="Orders",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_orders(
    rfq_id: Annotated[float | None, Field(description="Filter by RFQ id.")] = None,
    state: Annotated[OrderState | None, Field(description="Filter by order state.")] = None,
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    currency: Annotated[Currency | None, Field(description="Quote currency filter.")] = None,
    base_currency: Annotated[
        Currency | None, Field(description="Base currency filter.")
    ] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List the desk's orders."""
    client = await get_paradigm_client()
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
    name="paradigm_order",
    title="Order",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_order(
    order_id: Annotated[str, Field(description="Paradigm order id.")],
) -> Any:
    """Fetch a single order by id."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/orders/{order_id}/")


@server.tool(
    name="paradigm_post_order",
    title="Post Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_post_order(
    rfq_id: Annotated[str, Field(description="The RFQ to quote/cross.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    quantity: Annotated[str, Field(description="Order quantity (decimal string).")],
    type: Annotated[OrderType, Field(description="LIMIT or HIDDEN.")] = "LIMIT",
    time_in_force: Annotated[
        TimeInForce,
        Field(description="Maker quoting = GOOD_TILL_CANCELED; taker crossing = FILL_OR_KILL."),
    ] = "GOOD_TILL_CANCELED",
    price: Annotated[
        str | None, Field(description="Order price (decimal string). Required for LIMIT.")
    ] = None,
    legs: Annotated[
        list[OrderLeg] | None,
        Field(description="Per-leg prices for multi-leg structures."),
    ] = None,
    account_name: Annotated[
        str | None, Field(description="Account to use (omit for desk default).", max_length=256)
    ] = None,
    label: Annotated[
        str | None, Field(description="Caller idempotency label.", max_length=128)
    ] = None,
) -> Any:
    """Post an order against an RFQ.

    Order endpoint is async-first: the response state is always
    ``PENDING`` with zeroed fill quantities. Poll ``paradigm_order`` or
    subscribe to the ``order`` channel for terminal state. Gate behind
    explicit user confirmation — this puts money on the wire.
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
    return await client.post("/v2/drfq/orders/", json_body=body)


@server.tool(
    name="paradigm_update_order",
    title="Update Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_update_order(
    order_id: Annotated[str, Field(description="Order id to amend.")],
    rfq_id: Annotated[str, Field(description="The RFQ the order is against.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    quantity: Annotated[str, Field(description="New quantity (decimal string).")],
    type: Annotated[OrderType, Field(description="LIMIT or HIDDEN.")] = "LIMIT",
    time_in_force: Annotated[TimeInForce, Field(description="TIF.")] = "GOOD_TILL_CANCELED",
    price: Annotated[str | None, Field(description="New price (decimal string).")] = None,
    legs: Annotated[
        list[OrderLeg] | None,
        Field(description="Per-leg prices for multi-leg structures."),
    ] = None,
    account_name: Annotated[str | None, Field(description="Account name.")] = None,
    label: Annotated[str | None, Field(description="Caller idempotency label.")] = None,
) -> Any:
    """Amend an existing order (price / quantity)."""
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
    return await client.put(f"/v2/drfq/orders/{order_id}/", json_body=body)


@server.tool(
    name="paradigm_cancel_order",
    title="Cancel Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_cancel_order(
    order_id: Annotated[str, Field(description="Order id to cancel.")],
) -> dict[str, Any]:
    """Cancel a single order."""
    client = await get_paradigm_client()
    await client.delete(f"/v2/drfq/orders/{order_id}/")
    return {"order_id": order_id, "canceled": True}


@server.tool(
    name="paradigm_cancel_orders_batch",
    title="Cancel Orders (Batch)",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_cancel_orders_batch(
    rfq_id: Annotated[float | None, Field(description="Cancel orders against this RFQ.")] = None,
    state: Annotated[OrderState | None, Field(description="Cancel orders in this state.")] = None,
    venue: Annotated[Venue | None, Field(description="Cancel orders on this venue.")] = None,
    currency: Annotated[Currency | None, Field(description="Quote currency filter.")] = None,
    base_currency: Annotated[Currency | None, Field(description="Base currency filter.")] = None,
) -> Any:
    """Batch-cancel orders by filter.

    Returns ``{successes: {count, order_ids}, failures: {count, order_ids}}``.
    May come back as HTTP 207 when partially successful; the body shape
    is the same in either case.
    """
    client = await get_paradigm_client()
    return await client.delete(
        "/v2/drfq/orders/",
        rfq_id=rfq_id,
        state=state,
        venue=venue,
        currency=currency,
        base_currency=base_currency,
    )
