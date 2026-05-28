"""FSPD orders: list/single, post/replace, cancel."""

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
    order_id: Annotated[str | None, Field(description="If set, fetches a single order.")] = None,
    strategy_id: Annotated[str | None, Field(description="Filter by strategy.")] = None,
    state: Annotated[OrderState | None, Field(description="Order state.")] = None,
    venue: Annotated[Venue | None, Field(description="Venue filter.")] = None,
    kind: Annotated[Kind | None, Field(description="ANY or FUTURE.")] = None,
    type: Annotated[OrderType | None, Field(description="LIMIT or MARKET.")] = None,
    settlement_currency: Annotated[
        SettlementCurrency | None, Field(description="Settlement currency.")
    ] = None,
    from_order_id: Annotated[str | None, Field(description="Cursor.")] = None,
) -> Any:
    """List FSPD orders for the desk, or fetch one by id."""
    client = await get_fspd_client()
    if order_id is not None:
        return await client.get(f"/v1/fs/orders/{order_id}")
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
    name="paradigm_fspd_post_order",
    title="FSPD Post / Replace Order",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_fspd_post_order(
    strategy_id: Annotated[str, Field(description="FSPD strategy to trade.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    amount_decimal: Annotated[str, Field(description="Order size (decimal) in clearing currency.")],
    type: Annotated[OrderType, Field(description="LIMIT or MARKET.")] = "LIMIT",
    price: Annotated[str | None, Field(description="Limit price (decimal).")] = None,
    time_in_force: Annotated[TimeInForce, Field(description="GTC or IOC.")] = "GOOD_TILL_CANCELED",
    post_only: Annotated[bool | None, Field(description="Post-only flag.")] = None,
    label: Annotated[str | None, Field(description="Caller label.")] = None,
    account_name: Annotated[str | None, Field(description="Venue account name.")] = None,
    order_id: Annotated[
        str | None,
        Field(description="If set, replaces the existing order (POST /replace) instead of new."),
    ] = None,
) -> Any:
    """Post a new FSPD order, or replace one if ``order_id`` is set.

    Destructive — puts money on the wire.
    """
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
    if order_id is not None:
        return await client.post(f"/v1/fs/orders/{order_id}/replace", json_body=body)
    return await client.post("/v1/fs/orders", json_body=body)


@server.tool(
    name="paradigm_fspd_cancel",
    title="FSPD Cancel",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_fspd_cancel(
    order_id: Annotated[
        str | None,
        Field(
            description="If set, cancels a single order; otherwise cancels all (with optional label)."
        ),
    ] = None,
    label: Annotated[str | None, Field(description="Cancel only orders with this label.")] = None,
) -> dict[str, Any]:
    """Cancel a single FSPD order, or all orders for the desk (optionally by label)."""
    client = await get_fspd_client()
    if order_id is not None:
        await client.delete(f"/v1/fs/orders/{order_id}")
        return {"order_id": order_id, "canceled": True}
    await client.delete("/v1/fs/orders", label=label)
    return {"label": label, "canceled_all": True}
