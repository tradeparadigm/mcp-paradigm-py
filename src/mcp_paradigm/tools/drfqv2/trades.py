"""DRFQv2 trades — single, list, or public tape via ``mode`` param."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
TradeState = Literal["COMPLETED", "PENDING", "REJECTED"]


@server.tool(
    name="paradigm_drfqv2_trades",
    title="DRFQv2 Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_trades(
    trade_id: Annotated[str | None, Field(description="If set, fetches one trade.")] = None,
    mode: Annotated[
        Literal["desk", "tape"],
        Field(description="'desk' = your trades; 'tape' = public anonymized tape."),
    ] = "desk",
    state: Annotated[TradeState | None, Field(description="State filter.")] = None,
    venue: Annotated[Venue | None, Field(description="Venue filter.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy code (tape mode).")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List trades for the desk, fetch one, or read the public tape."""
    client = await get_paradigm_client()
    if trade_id is not None:
        return await client.get(f"/v2/drfq/trades/{trade_id}/")
    if mode == "tape":
        return await client.get(
            "/v2/drfq/trade_tape/",
            venue=venue,
            strategies=strategies,
            product_codes=product_codes,
            cursor=cursor,
            page_size=page_size,
        )
    return await client.get(
        "/v2/drfq/trades/",
        state=state,
        venue=venue,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )
