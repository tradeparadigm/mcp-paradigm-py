"""DRFQv2 reference data: instruments + counterparties.

Platform state is part of ``paradigm_desk_overview``. Single-instrument
fetch is via ``paradigm_drfqv2_instruments(instrument_id=...)``.
"""

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
    name="paradigm_drfqv2_instruments",
    title="DRFQv2 Instruments",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_instruments(
    instrument_id: Annotated[
        str | None, Field(description="If set, fetches a single instrument by id.")
    ] = None,
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
    """List or fetch a single DRFQv2 instrument (including expired)."""
    client = await get_paradigm_client()
    if instrument_id is not None:
        return await client.get(f"/v2/drfq/instruments/{instrument_id}/")
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
    name="paradigm_drfqv2_counterparties",
    title="DRFQv2 Counterparties",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_counterparties(
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
