"""OBv1 Market Maker Protection — status + reset in one tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client


# See drfqv2/mmp.py for the rationale on the destructiveHint annotation.
@server.tool(
    name="paradigm_obv1_mmp",
    title="OBv1 MMP",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_obv1_mmp(
    action: Annotated[
        Literal["status", "reset"],
        Field(description="'status' to read; 'reset' to re-arm the desk."),
    ] = "status",
) -> Any:
    """OBv1 MMP status, or reset to re-arm the desk."""
    client = await get_paradigm_client()
    if action == "reset":
        await client.patch("/v1/ob/mmp/status/", json_body={"rate_limit_hit": False})
        return {"rate_limit_hit": False, "reset": True}
    return await client.get("/v1/ob/mmp/status/")
