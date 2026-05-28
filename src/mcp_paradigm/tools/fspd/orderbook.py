"""FSPD orderbook — full depth by default, BBO summary on demand."""

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
    summary: Annotated[
        bool,
        Field(description="True returns BBO summary only; false (default) returns full depth."),
    ] = False,
) -> Any:
    """Orderbook for an FSPD strategy — full asks/bids depth by default,
    BBO summary if ``summary=True``."""
    client = await get_fspd_client()
    suffix = "order-book-summary" if summary else "order-book"
    return await client.get(f"/v1/fs/instruments/{strategy_id}/{suffix}")
