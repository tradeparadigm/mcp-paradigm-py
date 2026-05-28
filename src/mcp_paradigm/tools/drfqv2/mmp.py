"""DRFQv2 Market Maker Protection — status + reset in one tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client


@server.tool(
    name="paradigm_drfqv2_mmp",
    title="DRFQv2 MMP",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
)
async def paradigm_drfqv2_mmp(
    action: Annotated[
        Literal["status", "reset"],
        Field(description="'status' to read current state; 'reset' to re-arm the desk."),
    ] = "status",
) -> Any:
    """DRFQv2 Market Maker Protection — read status or reset the flag.

    ``reset`` is destructive (re-arms the desk). Only call after the
    trigger has been investigated.
    """
    client = await get_paradigm_client()
    if action == "reset":
        await client.patch("/v2/drfq/mmp/status/", json_body={"rate_limit_hit": False})
        return {"rate_limit_hit": False, "reset": True}
    return await client.get("/v2/drfq/mmp/status/")
