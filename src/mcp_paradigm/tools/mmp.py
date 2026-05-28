"""Market Maker Protection (MMP) tools."""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client


@server.tool(
    name="paradigm_mmp_status",
    title="MMP Status",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_mmp_status() -> Any:
    """Current Market Maker Protection status — ``rate_limit_hit`` boolean."""
    client = await get_paradigm_client()
    return await client.get("/v2/drfq/mmp/status/")


@server.tool(
    name="paradigm_mmp_reset",
    title="MMP Reset",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_mmp_reset() -> dict[str, Any]:
    """Reset the MMP flag to re-arm the desk for quoting.

    Only call after you've confirmed the trigger was investigated.
    """
    client = await get_paradigm_client()
    await client.patch("/v2/drfq/mmp/status/", json_body={"rate_limit_hit": False})
    return {"rate_limit_hit": False, "reset": True}
