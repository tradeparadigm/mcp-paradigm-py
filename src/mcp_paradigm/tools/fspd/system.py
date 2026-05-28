"""FSPD system status tools."""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_system_state",
    title="FSPD System State",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_system_state() -> Any:
    """Operational state of the FSPD system."""
    client = await get_fspd_client()
    return await client.get("/v1/fs/system/state")


@server.tool(
    name="paradigm_fspd_system_time",
    title="FSPD System Time",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_system_time() -> Any:
    """FSPD server time (unix nanoseconds)."""
    client = await get_fspd_client()
    return await client.get("/v1/fs/system/time")
