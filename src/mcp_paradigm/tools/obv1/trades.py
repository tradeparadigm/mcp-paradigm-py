"""OBv1 trades + blotter + tape, unified by ``mode`` param."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

TradeStatus = Literal["COMPLETED", "PENDING", "REJECTED"]


@server.tool(
    name="paradigm_obv1_trades",
    title="OBv1 Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_trades(
    trade_id: Annotated[str | None, Field(description="If set, fetches one trade.")] = None,
    mode: Annotated[
        Literal["trades", "blotter", "tape"],
        Field(
            description="'trades' = all visible; 'blotter' = desk's trades; 'tape' = public anonymized."
        ),
    ] = "trades",
    status: Annotated[TradeStatus | None, Field(description="Trade status.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy codes (comma).")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    hide_public: Annotated[bool | None, Field(description="Hide non-participant.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """OBv1 trades — single, desk-only blotter, all visible, or public tape."""
    client = await get_paradigm_client()
    if trade_id is not None:
        return await client.get(f"/v1/ob/trades/{trade_id}/")
    if mode == "blotter":
        return await client.get(
            "/v1/ob/blotter/", status=status, cursor=cursor, page_size=page_size
        )
    if mode == "tape":
        return await client.get(
            "/v1/ob/trade_tape/",
            strategies=strategies,
            product_codes=product_codes,
            cursor=cursor,
            page_size=page_size,
        )
    return await client.get(
        "/v1/ob/trades/",
        status=status,
        strategies=strategies,
        product_codes=product_codes,
        hide_public=hide_public,
        cursor=cursor,
        page_size=page_size,
    )
