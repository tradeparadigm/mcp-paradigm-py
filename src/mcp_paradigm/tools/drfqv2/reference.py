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


def _desk_supports_venue(desk: Any, venue: str) -> bool:
    """True if a counterparty desk lists ``venue`` among the venues it trades.

    Each desk carries a ``venues`` field; it may be a list of bare venue
    codes (``["PRDX", "DBT"]``) or a list of objects keyed by ``name`` /
    ``venue`` / ``code``. Match case-insensitively across both shapes.
    """
    if not isinstance(desk, dict):
        return False
    venues = desk.get("venues")
    if not isinstance(venues, list):
        return False
    target = venue.upper()
    for entry in venues:
        if isinstance(entry, str):
            name: Any = entry
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("venue") or entry.get("code")
        else:
            name = None
        if name is not None and str(name).upper() == target:
            return True
    return False


def _list_items(resp: Any) -> list[Any]:
    """Pull the list of records out of a Paradigm list response envelope."""
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for key in ("results", "data", "counterparties"):
            value = resp.get(key)
            if isinstance(value, list):
                return value
    return []


def _next_cursor(resp: Any) -> str | None:
    """Pull the next-page cursor token out of a list response, if any."""
    if not isinstance(resp, dict):
        return None
    for key in ("next", "next_cursor", "cursor"):
        value = resp.get(key)
        # DRF-style `next` is a full URL we can't reuse as a cursor; only
        # follow opaque cursor tokens.
        if isinstance(value, str) and value and "://" not in value:
            return value
    return None


@server.tool(
    name="paradigm_drfqv2_counterparties",
    title="DRFQv2 Counterparties",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_counterparties(
    venue: Annotated[
        str | None,
        Field(
            description=(
                "Filter to desks that support this settlement venue "
                "(e.g. 'PRDX', 'DBT'). When set, every page is scanned "
                "and only matching desks are returned, so the result is "
                "the complete set of LPs reachable for that venue."
            )
        ),
    ] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List counterparty desks the firm can RFQ.

    Each desk exposes ``desk_name``, ``firm_name``, ``groups``, and
    ``venues`` — the settlement venues that desk can trade. Use the
    ``venues`` field (or the ``venue`` filter) to resolve which LPs can
    quote a given venue before calling ``paradigm_drfqv2_create_rfq``;
    a desk that doesn't list a venue can't be quoted there.

    Without ``venue`` this returns one page (honouring ``cursor`` /
    ``page_size``). With ``venue`` set it pages through every desk and
    returns the full filtered set as
    ``{"results": [...], "count": N, "venue": ..., "scanned": M}`` —
    so "all LPs that support PRDX" is precisely resolvable in one call.
    """
    client = await get_paradigm_client()
    if venue is None:
        return await client.get(
            "/v2/drfq/counterparties/",
            cursor=cursor,
            page_size=page_size,
        )

    matched: list[Any] = []
    scanned = 0
    page_cursor = cursor
    # Bound the walk so a misbehaving cursor can never loop forever.
    for _ in range(100):
        resp = await client.get(
            "/v2/drfq/counterparties/",
            cursor=page_cursor,
            page_size=page_size,
        )
        items = _list_items(resp)
        scanned += len(items)
        matched.extend(d for d in items if _desk_supports_venue(d, venue))
        page_cursor = _next_cursor(resp)
        if not page_cursor:
            break
    return {
        "results": matched,
        "count": len(matched),
        "venue": venue,
        "scanned": scanned,
    }
