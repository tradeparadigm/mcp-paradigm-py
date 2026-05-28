"""OBv1 block trades, blotter, and public trade tape."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

TradeStatus = Literal["COMPLETED", "PENDING", "REJECTED"]


@server.tool(
    name="paradigm_obv1_trades",
    title="OBv1 Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_trades(
    status: Annotated[TradeStatus | None, Field(description="Trade status.")] = None,
    strategies: Annotated[
        str | None, Field(description="Strategy codes (comma-separated).")
    ] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    hide_public: Annotated[bool | None, Field(description="Hide non-participant trades.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List OBv1 block trades visible to the desk."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/trades/",
        status=status,
        strategies=strategies,
        product_codes=product_codes,
        hide_public=hide_public,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_obv1_trade",
    title="OBv1 Trade",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_trade(
    trade_id: Annotated[str, Field(description="Trade id.")],
) -> Any:
    """Fetch detailed BlockTrade if the requesting desk is part of it."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/trades/{trade_id}/")


@server.tool(
    name="paradigm_obv1_blotter",
    title="OBv1 Blotter",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_blotter(
    status: Annotated[TradeStatus | None, Field(description="Trade status.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """The trading desk's block trades, ordered by traded_at descending."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/blotter/",
        status=status,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_obv1_trade_tape",
    title="OBv1 Trade Tape",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_trade_tape(
    strategies: Annotated[
        str | None, Field(description="Strategy codes (comma-separated).")
    ] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """Public anonymized OBv1 trade tape."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/trade_tape/",
        strategies=strategies,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )
