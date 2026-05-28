"""Trade tools: desk trades and the public tape."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
TradeState = Literal["COMPLETED", "PENDING", "REJECTED"]


@server.tool(
    name="paradigm_trades",
    title="Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_trades(
    state: Annotated[TradeState | None, Field(description="Filter by trade state.")] = None,
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """Cleared block trades for the desk."""
    client = await get_paradigm_client()
    return await client.get(
        "/v2/drfq/trades/",
        state=state,
        venue=venue,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_trade",
    title="Trade",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_trade(
    trade_id: Annotated[str, Field(description="Paradigm trade id.")],
) -> Any:
    """Fetch a single trade."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/trades/{trade_id}/")


@server.tool(
    name="paradigm_trade_tape",
    title="Trade Tape",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_trade_tape(
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy code filter.")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """Public anonymized trade tape across the network."""
    client = await get_paradigm_client()
    return await client.get(
        "/v2/drfq/trade_tape/",
        venue=venue,
        strategies=strategies,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )
