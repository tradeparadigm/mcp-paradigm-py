"""FSPD trades: list with filters, or fetch one by id."""

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
    trade_id: Annotated[str | None, Field(description="If set, fetches one trade.")] = None,
    strategy_id: Annotated[str | None, Field(description="Strategy filter.")] = None,
    order_id: Annotated[str | None, Field(description="Order filter.")] = None,
    venue: Annotated[str | None, Field(description="Venue filter.")] = None,
    kind: Annotated[str | None, Field(description="Instrument kind.")] = None,
    role: Annotated[str | None, Field(description="maker or taker.")] = None,
    settlement_currency: Annotated[str | None, Field(description="Settlement currency.")] = None,
    state: Annotated[str | None, Field(description="Trade state.")] = None,
    inverse_margined: Annotated[bool | None, Field(description="Inverse-margined.")] = None,
    from_trade_id: Annotated[str | None, Field(description="Cursor.")] = None,
) -> Any:
    """List FSPD trades for the desk, or fetch one by id."""
    client = await get_fspd_client()
    if trade_id is not None:
        return await client.get(f"/v1/fs/trades/{trade_id}")
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
