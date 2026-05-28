"""FSPD Market Maker Protection."""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_mmp_status",
    title="FSPD MMP Status",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_mmp_status() -> Any:
    """Current FSPD Market Maker Protection status."""
    client = await get_fspd_client()
    return await client.get("/v1/fs/mmp/status")


@server.tool(
    name="paradigm_fspd_mmp_reset",
    title="FSPD MMP Reset",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_fspd_mmp_reset() -> dict[str, Any]:
    """Reset the FSPD MMP flag to re-arm the desk."""
    client = await get_fspd_client()
    await client.patch("/v1/fs/mmp/status", json_body={})
    return {"reset": True}
