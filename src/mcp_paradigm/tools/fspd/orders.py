"""FSPD order lifecycle: list, get, create, replace, cancel."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client

Side = Literal["BUY", "SELL"]
OrderType = Literal["LIMIT", "MARKET"]
OrderState = Literal["OPEN", "CLOSED", "PENDING"]
TimeInForce = Literal["GOOD_TILL_CANCELED", "IMMEDIATE_OR_CANCEL"]
Venue = Literal["BYB", "DBT", "BIT"]
Kind = Literal["ANY", "FUTURE"]
SettlementCurrency = Literal["USD", "BTC", "SOL", "AVAX", "ETH"]


@server.tool(
    name="paradigm_fspd_orders",
    title="FSPD Orders",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_orders(
    strategy_id: Annotated[str | None, Field(description="Filter by strategy id.")] = None,
    state: Annotated[OrderState | None, Field(description="Filter by order state.")] = None,
    venue: Annotated[Venue | None, Field(description="Clearing venue filter.")] = None,
    kind: Annotated[Kind | None, Field(description="ANY or FUTURE.")] = None,
    type: Annotated[OrderType | None, Field(description="LIMIT or MARKET.")] = None,
    settlement_currency: Annotated[
        SettlementCurrency | None, Field(description="Settlement currency.")
    ] = None,
    from_order_id: Annotated[
        str | None, Field(description="Cursor — start after this order id.")
    ] = None,
) -> Any:
    """List FSPD orders for the desk."""
    client = await get_fspd_client()
    return await client.get(
        "/v1/fs/orders",
        strategyId=strategy_id,
        state=state,
        venue=venue,
        kind=kind,
        type=type,
        settlementCurrency=settlement_currency,
        fromOrderId=from_order_id,
    )


@server.tool(
    name="paradigm_fspd_order",
    title="FSPD Order",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_order(
    order_id: Annotated[str, Field(description="FSPD order id.")],
) -> Any:
    """Fetch a single FSPD order, with its event history."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/orders/{order_id}")


@server.tool(
    name="paradigm_fspd_post_order",
    title="FSPD Post Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_fspd_post_order(
    strategy_id: Annotated[str, Field(description="FSPD strategy to trade.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    amount_decimal: Annotated[
        str, Field(description="Order size (decimal string) in clearing currency.")
    ],
    type: Annotated[OrderType, Field(description="LIMIT or MARKET.")] = "LIMIT",
    price: Annotated[
        str | None,
        Field(description="Limit price (decimal string in quote currency). Required for LIMIT."),
    ] = None,
    time_in_force: Annotated[
        TimeInForce, Field(description="GOOD_TILL_CANCELED or IMMEDIATE_OR_CANCEL.")
    ] = "GOOD_TILL_CANCELED",
    post_only: Annotated[
        bool | None, Field(description="Post-only flag — reject if would cross.")
    ] = None,
    label: Annotated[str | None, Field(description="Caller idempotency / grouping label.")] = None,
    account_name: Annotated[
        str | None, Field(description="Venue API credential account name.")
    ] = None,
) -> Any:
    """Post an FSPD order. Destructive — puts money on the wire."""
    client = await get_fspd_client()
    body: dict[str, Any] = {
        "strategy_id": strategy_id,
        "side": side,
        "amount_decimal": amount_decimal,
        "type": type,
        "time_in_force": time_in_force,
    }
    if price is not None:
        body["price"] = price
    if post_only is not None:
        body["post_only"] = post_only
    if label is not None:
        body["label"] = label
    if account_name is not None:
        body["account_name"] = account_name
    return await client.post("/v1/fs/orders", json_body=body)


@server.tool(
    name="paradigm_fspd_replace_order",
    title="FSPD Replace Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_fspd_replace_order(
    order_id: Annotated[str, Field(description="Order id to replace.")],
    strategy_id: Annotated[str, Field(description="FSPD strategy.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    amount_decimal: Annotated[str, Field(description="New order size (decimal).")],
    type: Annotated[OrderType, Field(description="LIMIT or MARKET.")] = "LIMIT",
    price: Annotated[str | None, Field(description="New limit price.")] = None,
    time_in_force: Annotated[TimeInForce, Field(description="TIF.")] = "GOOD_TILL_CANCELED",
    post_only: Annotated[bool | None, Field(description="Post-only flag.")] = None,
    label: Annotated[str | None, Field(description="Caller label.")] = None,
    account_name: Annotated[str | None, Field(description="Venue account name.")] = None,
) -> Any:
    """Replace an existing FSPD order (cancel + new in one call)."""
    client = await get_fspd_client()
    body: dict[str, Any] = {
        "strategy_id": strategy_id,
        "side": side,
        "amount_decimal": amount_decimal,
        "type": type,
        "time_in_force": time_in_force,
    }
    if price is not None:
        body["price"] = price
    if post_only is not None:
        body["post_only"] = post_only
    if label is not None:
        body["label"] = label
    if account_name is not None:
        body["account_name"] = account_name
    return await client.post(f"/v1/fs/orders/{order_id}/replace", json_body=body)


@server.tool(
    name="paradigm_fspd_cancel_order",
    title="FSPD Cancel Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_fspd_cancel_order(
    order_id: Annotated[str, Field(description="Order id to cancel.")],
) -> dict[str, Any]:
    """Cancel a single FSPD order."""
    client = await get_fspd_client()
    await client.delete(f"/v1/fs/orders/{order_id}")
    return {"order_id": order_id, "canceled": True}


@server.tool(
    name="paradigm_fspd_cancel_all_orders",
    title="FSPD Cancel All Orders",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_fspd_cancel_all_orders(
    label: Annotated[str | None, Field(description="Cancel only orders with this label.")] = None,
) -> dict[str, Any]:
    """Cancel all FSPD orders for the desk, optionally filtered by label."""
    client = await get_fspd_client()
    await client.delete("/v1/fs/orders", label=label)
    return {"label": label, "canceled_all": True}
