"""OBv1 maker quotes — create, list, update, cancel."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Side = Literal["BUY", "SELL"]
QuoteSide = Literal["Buy", "Sell"]
QuoteStatus = Literal["OPEN", "CLOSED"]
Currency = Literal["AVAX", "BCH", "BTC", "ETH", "SOL", "TONCOIN", "TRX", "USD", "USDC", "XRP"]


class QuoteLeg(BaseModel):
    instrument: str = Field(description="Venue-native instrument name.")
    price: str = Field(description="Leg price (decimal string).")


@server.tool(
    name="paradigm_obv1_quotes",
    title="OBv1 Desk Quotes",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_quotes(
    rfq_id: Annotated[str | None, Field(description="Filter by OB id.")] = None,
    status: Annotated[QuoteStatus | None, Field(description="OPEN or CLOSED.")] = None,
    side: Annotated[QuoteSide | None, Field(description="Buy or Sell.")] = None,
    currency: Annotated[Currency | None, Field(description="Currency filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List quotes belonging to the desk."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/quotes/",
        rfq_id=rfq_id,
        status=status,
        side=side,
        currency=currency,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_obv1_quote",
    title="OBv1 Quote",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_quote(
    quote_id: Annotated[str, Field(description="Quote id.")],
) -> Any:
    """Fetch a single quote by id."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/quotes/{quote_id}/")


@server.tool(
    name="paradigm_obv1_post_quote",
    title="OBv1 Post Quote",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_obv1_post_quote(
    ob_id: Annotated[str, Field(description="OB id to quote on.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    quantity: Annotated[str, Field(description="Quote quantity (decimal).")],
    legs: Annotated[list[QuoteLeg], Field(description="Per-leg prices.", min_length=1)],
    account: Annotated[str, Field(description="Account name (required).", max_length=256)],
    client_order_id: Annotated[
        str | None, Field(description="Caller idempotency id.", max_length=64)
    ] = None,
    post_only: Annotated[bool | None, Field(description="Post-only flag.")] = None,
    ioc: Annotated[bool | None, Field(description="IOC flag.")] = None,
) -> Any:
    """Post a maker quote against an OBv1 market.

    Destructive — adds liquidity that may be hit immediately if it
    crosses the book (unless ``post_only`` is set).
    """
    client = await get_paradigm_client()
    body: dict[str, Any] = {
        "side": side,
        "quantity": quantity,
        "legs": [leg.model_dump() for leg in legs],
        "account": account,
    }
    if client_order_id is not None:
        body["client_order_id"] = client_order_id
    if post_only is not None:
        body["post_only"] = post_only
    if ioc is not None:
        body["ioc"] = ioc
    return await client.post(f"/v1/ob/rfqs/{ob_id}/quotes/", json_body=body)


@server.tool(
    name="paradigm_obv1_update_quote",
    title="OBv1 Update Quote",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def paradigm_obv1_update_quote(
    ob_id: Annotated[str, Field(description="OB id.")],
    quote_id: Annotated[str, Field(description="Quote id to replace.")],
    side: Annotated[Side, Field(description="BUY or SELL.")],
    quantity: Annotated[str, Field(description="New quantity.")],
    legs: Annotated[list[QuoteLeg], Field(description="Per-leg prices.", min_length=1)],
    account: Annotated[str, Field(description="Account name.", max_length=256)],
    client_order_id: Annotated[
        str | None, Field(description="Caller idempotency id.", max_length=64)
    ] = None,
    post_only: Annotated[bool | None, Field(description="Post-only flag.")] = None,
    ioc: Annotated[bool | None, Field(description="IOC flag.")] = None,
) -> Any:
    """Replace an existing OBv1 quote (cancel + new in one call)."""
    client = await get_paradigm_client()
    body: dict[str, Any] = {
        "side": side,
        "quantity": quantity,
        "legs": [leg.model_dump() for leg in legs],
        "account": account,
    }
    if client_order_id is not None:
        body["client_order_id"] = client_order_id
    if post_only is not None:
        body["post_only"] = post_only
    if ioc is not None:
        body["ioc"] = ioc
    return await client.put(f"/v1/ob/rfqs/{ob_id}/quotes/{quote_id}/", json_body=body)


@server.tool(
    name="paradigm_obv1_cancel_quote",
    title="OBv1 Cancel Quote",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_obv1_cancel_quote(
    quote_id: Annotated[str, Field(description="Quote id to cancel.")],
) -> dict[str, Any]:
    """Cancel a single OBv1 quote."""
    client = await get_paradigm_client()
    await client.delete(f"/v1/ob/quotes/{quote_id}/")
    return {"quote_id": quote_id, "canceled": True}


@server.tool(
    name="paradigm_obv1_cancel_quotes_batch",
    title="OBv1 Cancel Quotes (Batch)",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_obv1_cancel_quotes_batch(
    rfq_id: Annotated[str | None, Field(description="Cancel quotes on this OB.")] = None,
    side: Annotated[QuoteSide | None, Field(description="Buy or Sell only.")] = None,
    currency: Annotated[Currency | None, Field(description="Currency filter.")] = None,
    price: Annotated[float | None, Field(description="Cancel only at/around this price.")] = None,
) -> Any:
    """Batch-cancel quotes by filter. Returns an action_id."""
    client = await get_paradigm_client()
    return await client.delete(
        "/v1/ob/quotes/",
        rfq_id=rfq_id,
        side=side,
        currency=currency,
        price=price,
    )
