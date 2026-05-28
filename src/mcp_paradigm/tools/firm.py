"""Firm-level cross-product tools: identity, positions, leaderboard."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]


@server.tool(
    name="paradigm_identity_credentials",
    title="Identity Credentials",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_identity_credentials(
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """Active venue API credentials registered for the trading desk."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/identity/credentials/",
        venue=venue,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_positions",
    title="Positions",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_positions(
    venue: Annotated[str | None, Field(description="Filter by venue.")] = None,
    product_code: Annotated[str | None, Field(description="Filter by product code.")] = None,
    account_name: Annotated[str | None, Field(description="Filter by API account name.")] = None,
) -> Any:
    """All positions for the trading desk across venues."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/positions/",
        venue=venue,
        product_code=product_code,
        account_name=account_name,
    )


@server.tool(
    name="paradigm_positions_refresh",
    title="Positions Refresh",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
)
async def paradigm_positions_refresh() -> dict[str, Any]:
    """Trigger an async refresh of the desk's positions cache. Returns 202."""
    client = await get_paradigm_client()
    await client.post("/v1/positions/refresh/", json_body={})
    return {"refresh_triggered": True}


@server.tool(
    name="paradigm_leaderboard_trade_volume",
    title="Leaderboard: Trade Volume",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_leaderboard_trade_volume(
    currencies: Annotated[str | None, Field(description="Comma-separated currencies.")] = None,
    venues: Annotated[str | None, Field(description="Comma-separated venues.")] = None,
    instrument_kinds: Annotated[
        str | None, Field(description="Comma-separated instrument kinds.")
    ] = None,
    protocols: Annotated[
        str | None, Field(description="Comma-separated protocols (D1, OB, RFQ).")
    ] = None,
    start: Annotated[float | None, Field(description="Start time (unix ms).")] = None,
    end: Annotated[float | None, Field(description="End time (unix ms).")] = None,
) -> Any:
    """Cross-firm trade volume leaderboard."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/leaderboard/trade_volume/",
        currencies=currencies,
        venues=venues,
        instrument_kinds=instrument_kinds,
        protocols=protocols,
        start=start,
        end=end,
    )


@server.tool(
    name="paradigm_leaderboard_liquidity_fills",
    title="Leaderboard: Liquidity Fills",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_leaderboard_liquidity_fills(
    currencies: Annotated[str | None, Field(description="Comma-separated currencies.")] = None,
    venues: Annotated[str | None, Field(description="Comma-separated venues.")] = None,
    instrument_kinds: Annotated[
        str | None, Field(description="Comma-separated instrument kinds.")
    ] = None,
    protocols: Annotated[
        str | None, Field(description="Comma-separated protocols (D1, OB, RFQ).")
    ] = None,
    strategies: Annotated[str | None, Field(description="Comma-separated strategy codes.")] = None,
    start: Annotated[float | None, Field(description="Start time (unix ms).")] = None,
    end: Annotated[float | None, Field(description="End time (unix ms).")] = None,
) -> Any:
    """Liquidity fills leaderboard — quote rate, fill rate, spread rank."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/leaderboard/liquidity/fills",
        currencies=currencies,
        venues=venues,
        instrument_kinds=instrument_kinds,
        protocols=protocols,
        strategies=strategies,
        start=start,
        end=end,
    )


@server.tool(
    name="paradigm_leaderboard_liquidity_responses",
    title="Leaderboard: Liquidity Responses",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_leaderboard_liquidity_responses(
    currencies: Annotated[str | None, Field(description="Comma-separated currencies.")] = None,
    venues: Annotated[str | None, Field(description="Comma-separated venues.")] = None,
    instrument_kinds: Annotated[
        str | None, Field(description="Comma-separated instrument kinds.")
    ] = None,
    protocols: Annotated[str | None, Field(description="Comma-separated protocols.")] = None,
    strategies: Annotated[str | None, Field(description="Comma-separated strategies.")] = None,
    start: Annotated[float | None, Field(description="Start time (unix ms).")] = None,
    end: Annotated[float | None, Field(description="End time (unix ms).")] = None,
) -> Any:
    """Liquidity response leaderboard — response-time buckets and quote rate."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/leaderboard/liquidity/responses",
        currencies=currencies,
        venues=venues,
        instrument_kinds=instrument_kinds,
        protocols=protocols,
        strategies=strategies,
        start=start,
        end=end,
    )


@server.tool(
    name="paradigm_leaderboard_set_preferences",
    title="Leaderboard: Set Preferences",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
)
async def paradigm_leaderboard_set_preferences(
    disabled_leaderboard_anonymity: Annotated[
        bool, Field(description="True to show firm name on leaderboards; False for anonymous.")
    ],
) -> Any:
    """Create or update the firm's leaderboard anonymity preference."""
    client = await get_paradigm_client()
    return await client.put(
        "/v1/leaderboard/preferences/",
        json_body={"disabled_leaderboard_anonymity": disabled_leaderboard_anonymity},
    )
