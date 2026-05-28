"""FSPD Market Maker Protection — status + reset in one tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


@server.tool(
    name="paradigm_fspd_mmp",
    title="FSPD MMP",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
)
async def paradigm_fspd_mmp(
    action: Annotated[
        Literal["status", "reset"],
        Field(description="'status' to read; 'reset' to re-arm the desk."),
    ] = "status",
) -> Any:
    """FSPD MMP status, or reset to re-arm the desk."""
    client = await get_fspd_client()
    if action == "reset":
        await client.patch("/v1/fs/mmp/status", json_body={})
        return {"reset": True}
    return await client.get("/v1/fs/mmp/status")
