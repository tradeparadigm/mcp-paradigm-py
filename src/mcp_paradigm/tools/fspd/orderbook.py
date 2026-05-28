"""FSPD orderbook tools — full depth and BBO summary."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_orderbook",
    title="FSPD Orderbook",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_orderbook(
    strategy_id: Annotated[str, Field(description="FSPD strategy id.")],
) -> Any:
    """Full orderbook (bids + asks with order_ids) for an FSPD strategy."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/instruments/{strategy_id}/order-book")


@server.tool(
    name="paradigm_fspd_orderbook_summary",
    title="FSPD Orderbook Summary",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_orderbook_summary(
    strategy_id: Annotated[str, Field(description="FSPD strategy id.")],
) -> Any:
    """BBO summary for an FSPD strategy — best bid/ask, last trade."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/instruments/{strategy_id}/order-book-summary")
