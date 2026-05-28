"""FSPD trade history tools."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_trades",
    title="FSPD Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_trades(
    strategy_id: Annotated[str | None, Field(description="Filter by strategy id.")] = None,
    order_id: Annotated[str | None, Field(description="Filter by order id.")] = None,
    venue: Annotated[str | None, Field(description="Clearing venue.")] = None,
    kind: Annotated[str | None, Field(description="Instrument kind.")] = None,
    role: Annotated[str | None, Field(description="User role: maker or taker.")] = None,
    settlement_currency: Annotated[str | None, Field(description="Settlement currency.")] = None,
    state: Annotated[str | None, Field(description="Trade state.")] = None,
    inverse_margined: Annotated[
        bool | None, Field(description="True for inverse-margined trades.")
    ] = None,
    from_trade_id: Annotated[
        str | None, Field(description="Cursor — start after this trade id.")
    ] = None,
) -> Any:
    """List FSPD trades for the desk."""
    client = await get_fspd_client()
    return await client.get(
        "/v1/fs/trades",
        strategyId=strategy_id,
        orderId=order_id,
        venue=venue,
        kind=kind,
        role=role,
        settlementCurrency=settlement_currency,
        state=state,
        inverseMargined=inverse_margined,
        fromTradeId=from_trade_id,
    )


@server.tool(
    name="paradigm_fspd_trade",
    title="FSPD Trade",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_trade(
    trade_id: Annotated[str, Field(description="FSPD trade id.")],
) -> Any:
    """Fetch a single FSPD trade, with its legs."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/trades/{trade_id}")
