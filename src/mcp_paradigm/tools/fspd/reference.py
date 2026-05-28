"""FSPD reference data: instruments, strategies, venues."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_fspd_client

InstrumentKind = Literal["ANY", "FUTURE", "SPOT"]
StrategyKind = Literal["ANY", "FUTURE", "SPOT_FUTURE"]
MarginType = Literal["INVERSE", "LINEAR"]
InstrumentState = Literal["ACTIVE", "SETTLED", "EXPIRED"]
SettlementCurrency = Literal["USD", "BTC", "SOL", "AVAX", "ETH"]


@server.tool(
    name="paradigm_fspd_instruments",
    title="FSPD Instruments",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_instruments(
    venue: Annotated[str | None, Field(description="Clearing venue filter.")] = None,
    kind: Annotated[InstrumentKind | None, Field(description="ANY, FUTURE, or SPOT.")] = None,
    margin_type: Annotated[MarginType | None, Field(description="INVERSE or LINEAR.")] = None,
    state: Annotated[InstrumentState | None, Field(description="ACTIVE, SETTLED, EXPIRED.")] = None,
    clearing_currency: Annotated[
        str | None, Field(description="Currency the order size is submitted in.")
    ] = None,
    settlement_currency: Annotated[
        SettlementCurrency | None, Field(description="Settlement currency.")
    ] = None,
    name: Annotated[str | None, Field(description="Paradigm instrument name.")] = None,
    venue_instrument_name: Annotated[
        str | None, Field(description="Venue-native instrument name.")
    ] = None,
) -> Any:
    """List FSPD instruments tradable on the desk."""
    client = await get_fspd_client()
    return await client.get(
        "/v1/fs/instruments",
        venue=venue,
        kind=kind,
        margin_type=margin_type,
        state=state,
        clearing_currency=clearing_currency,
        settlement_currency=settlement_currency,
        name=name,
        venue_instrument_name=venue_instrument_name,
    )


@server.tool(
    name="paradigm_fspd_strategies",
    title="FSPD Strategies",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_strategies(
    id: Annotated[str | None, Field(description="Filter by strategy id.")] = None,
    venue: Annotated[str | None, Field(description="Clearing venue.")] = None,
    kind: Annotated[StrategyKind | None, Field(description="ANY, FUTURE, SPOT_FUTURE.")] = None,
    margin_type: Annotated[MarginType | None, Field(description="INVERSE or LINEAR.")] = None,
    state: Annotated[InstrumentState | None, Field(description="ACTIVE, SETTLED, EXPIRED.")] = None,
    base_currency: Annotated[str | None, Field(description="Base currency filter.")] = None,
    clearing_currency: Annotated[str | None, Field(description="Clearing currency.")] = None,
    settlement_currency: Annotated[
        SettlementCurrency | None, Field(description="Settlement currency.")
    ] = None,
) -> Any:
    """List tradeable FSPD strategies (future spreads + spot/future)."""
    client = await get_fspd_client()
    return await client.get(
        "/v1/fs/strategies",
        id=id,
        venue=venue,
        kind=kind,
        marginType=margin_type,
        state=state,
        baseCurrency=base_currency,
        clearingCurrency=clearing_currency,
        settlementCurrency=settlement_currency,
    )


@server.tool(
    name="paradigm_fspd_strategy",
    title="FSPD Strategy",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_strategy(
    strategy_id: Annotated[str, Field(description="FSPD strategy id.")],
) -> Any:
    """Fetch a single FSPD strategy by id, with its legs."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/instruments/{strategy_id}")


@server.tool(
    name="paradigm_fspd_venues",
    title="FSPD Venues",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_venues() -> Any:
    """Status of all FSPD clearing venues."""
    client = await get_fspd_client()
    return await client.get("/v1/fs/venues")


@server.tool(
    name="paradigm_fspd_venue",
    title="FSPD Venue",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_fspd_venue(
    venue: Annotated[Literal["dbt", "byb", "bit"], Field(description="Venue code.")],
) -> Any:
    """Status of a single FSPD venue."""
    client = await get_fspd_client()
    return await client.get(f"/v1/fs/venues/{venue}")
