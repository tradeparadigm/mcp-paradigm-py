"""OBv1 taker fill orders. Read-only — fills against maker quotes."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client


@server.tool(
    name="paradigm_obv1_orders",
    title="OBv1 Fill Orders",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_orders(
    order_id: Annotated[str | None, Field(description="If set, fetches one order.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List OBv1 fill orders, or fetch one by id."""
    client = await get_paradigm_client()
    if order_id is not None:
        return await client.get(f"/v1/ob/orders/{order_id}/")
    return await client.get("/v1/ob/orders/", cursor=cursor, page_size=page_size)
