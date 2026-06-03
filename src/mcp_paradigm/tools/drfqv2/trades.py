"""DRFQv2 trades — single, list, or public tape via ``mode`` param."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.errors import normalize_rejection
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
TradeState = Literal["COMPLETED", "PENDING", "REJECTED"]


def _enrich_trade(trade: Any) -> Any:
    """Attach a structured ``rejection`` block to a REJECTED trade record.

    A trade list/get is a GET, so there's no per-record request id; the
    block is built from the trade's own fields and stamped with the time
    it was normalized. Non-rejected records pass through unchanged.
    """
    if not isinstance(trade, dict):
        return trade
    rejection = normalize_rejection(trade)
    if rejection is None:
        return trade
    return {**trade, "rejection": rejection}


def _enrich_trades(resp: Any) -> Any:
    """Map :func:`_enrich_trade` over a single trade or a list envelope."""
    if isinstance(resp, dict):
        for key in ("results", "data", "trades"):
            items = resp.get(key)
            if isinstance(items, list):
                return {**resp, key: [_enrich_trade(t) for t in items]}
        return _enrich_trade(resp)  # single-trade payload
    if isinstance(resp, list):
        return [_enrich_trade(t) for t in resp]
    return resp


@server.tool(
    name="paradigm_drfqv2_trades",
    title="DRFQv2 Trades",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_trades(
    trade_id: Annotated[str | None, Field(description="If set, fetches one trade.")] = None,
    mode: Annotated[
        Literal["desk", "tape"],
        Field(description="'desk' = your trades; 'tape' = public anonymized tape."),
    ] = "desk",
    state: Annotated[TradeState | None, Field(description="State filter.")] = None,
    venue: Annotated[Venue | None, Field(description="Venue filter.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy code (tape mode).")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List trades for the desk, fetch one, or read the public tape."""
    client = await get_paradigm_client()
    if trade_id is not None:
        return _enrich_trades(await client.get(f"/v2/drfq/trades/{trade_id}/"))
    if mode == "tape":
        return await client.get(
            "/v2/drfq/trade_tape/",
            venue=venue,
            strategies=strategies,
            product_codes=product_codes,
            cursor=cursor,
            page_size=page_size,
        )
    return _enrich_trades(
        await client.get(
            "/v2/drfq/trades/",
            state=state,
            venue=venue,
            product_codes=product_codes,
            cursor=cursor,
            page_size=page_size,
        )
    )
