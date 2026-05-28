"""FSPD system state + time, combined."""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.types import ToolAnnotations

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_system",
    title="FSPD System Status",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_system() -> dict[str, Any]:
    """FSPD operational state + server time in one call."""
    client = await get_fspd_client()
    state, time = await asyncio.gather(
        client.get("/v1/fs/system/state"),
        client.get("/v1/fs/system/time"),
    )
    return {"state": state, "time": time}
