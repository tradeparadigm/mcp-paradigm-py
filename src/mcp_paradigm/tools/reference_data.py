"""Reference data tools: instruments, counterparties, platform state."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
BaseCurrency = Literal["AVAX", "BCH", "BTC", "ETH", "SOL", "TONCOIN", "TRX", "XRP"]
InstrumentKind = Literal["FUTURE", "OPTION"]
MarginKind = Literal["INVERSE", "LINEAR"]
InstrumentState = Literal["ACTIVE", "EXPIRED"]


@server.tool(
    name="paradigm_instruments",
    title="Instruments",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_instruments(
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    base_currency: Annotated[
        BaseCurrency | None, Field(description="Filter by base currency.")
    ] = None,
    kind: Annotated[InstrumentKind | None, Field(description="FUTURE or OPTION.")] = None,
    margin_kind: Annotated[MarginKind | None, Field(description="INVERSE or LINEAR.")] = None,
    state: Annotated[InstrumentState | None, Field(description="ACTIVE or EXPIRED.")] = None,
    venue_instrument_name: Annotated[
        list[str] | None, Field(description="Venue-native instrument name(s).")
    ] = None,
    include_greeks: Annotated[bool | None, Field(description="Include greeks payload.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List tradable instruments supported on Paradigm."""
    client = await get_paradigm_client()
    return await client.get(
        "/v2/drfq/instruments/",
        venue=venue,
        base_currency=base_currency,
        kind=kind,
        margin_kind=margin_kind,
        state=state,
        venue_instrument_name=venue_instrument_name,
        include_greeks=include_greeks,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_instrument",
    title="Instrument",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_instrument(
    instrument_id: Annotated[str, Field(description="Paradigm instrument id.")],
) -> Any:
    """Fetch a single instrument by Paradigm id (including expired)."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/instruments/{instrument_id}/")


@server.tool(
    name="paradigm_counterparties",
    title="Counterparties",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_counterparties(
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List desks the firm can RFQ — desk_name, firm_name, groups, venues."""
    client = await get_paradigm_client()
    return await client.get(
        "/v2/drfq/counterparties/",
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_platform_state",
    title="Platform State",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_platform_state() -> Any:
    """Current and next DRFQv2 platform state (maintenance windows)."""
    client = await get_paradigm_client()
    return await client.get("/v2/drfq/platform_state/")
