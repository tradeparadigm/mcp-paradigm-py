"""FSPD orderbook — summary BBO by default, full depth on demand."""

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
    full: Annotated[
        bool,
        Field(description="True returns full asks/bids depth; false returns BBO summary."),
    ] = False,
) -> Any:
    """Orderbook for an FSPD strategy — BBO summary by default, full depth if ``full=True``."""
    client = await get_fspd_client()
    suffix = "order-book" if full else "order-book-summary"
    return await client.get(f"/v1/fs/instruments/{strategy_id}/{suffix}")
