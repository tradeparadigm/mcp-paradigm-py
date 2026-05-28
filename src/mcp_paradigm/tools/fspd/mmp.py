"""FSPD Market Maker Protection — status + reset in one tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client


# See drfqv2/mmp.py for the rationale on the destructiveHint annotation.
@server.tool(
    name="paradigm_fspd_mmp",
    title="FSPD MMP",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
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
        # Mirror the shape of DRFQv2/OBv1 reset payloads.
        await client.patch("/v1/fs/mmp/status", json_body={"rate_limit_hit": False})
        return {"rate_limit_hit": False, "reset": True}
    return await client.get("/v1/fs/mmp/status")
