"""OBv1 Market Maker Protection."""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client


@server.tool(
    name="paradigm_obv1_mmp_status",
    title="OBv1 MMP Status",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_mmp_status() -> Any:
    """Current OBv1 Market Maker Protection status."""
    client = await get_paradigm_client()
    return await client.get("/v1/ob/mmp/status/")


@server.tool(
    name="paradigm_obv1_mmp_reset",
    title="OBv1 MMP Reset",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_obv1_mmp_reset() -> dict[str, Any]:
    """Reset the OBv1 MMP flag to re-arm the desk."""
    client = await get_paradigm_client()
    await client.patch("/v1/ob/mmp/status/", json_body={"rate_limit_hit": False})
    return {"rate_limit_hit": False, "reset": True}
