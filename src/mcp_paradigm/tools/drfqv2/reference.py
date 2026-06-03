"""DRFQv2 reference data: instruments + counterparties.

Platform state is part of ``paradigm_desk_overview``. Single-instrument
fetch is via ``paradigm_drfqv2_instruments(instrument_id=...)``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.models import PermissiveModel
from mcp_paradigm.utils.paradigm_client import ParadigmClient, get_paradigm_client


class CounterpartiesResult(PermissiveModel):
    """Owned envelope for ``paradigm_drfqv2_counterparties`` (all modes).

    Single-page mode populates ``next_cursor``/``has_more``/``total``; the
    full-walk modes populate ``scanned``/``truncated`` (and ``venue`` /
    ``note`` when filtering). ``results`` holds raw upstream desk objects,
    passed through untouched.
    """

    results: Annotated[
        list[Any],
        Field(
            default_factory=list,
            description="Matched counterparty desks (raw upstream objects, each annotated with `prime_venue_enabled`).",
        ),
    ]
    count: Annotated[int | None, Field(description="Number of desks in `results`.")] = None
    next_cursor: Annotated[
        str | None,
        Field(
            description="Opaque cursor for the next page (single-page mode); pass back as `cursor`. Null when exhausted."
        ),
    ] = None
    has_more: Annotated[
        bool | None, Field(description="Whether another page exists (single-page mode).")
    ] = None
    total: Annotated[
        int | None,
        Field(
            description="Total desk count across all pages, when the API reports it (single-page mode)."
        ),
    ] = None
    scanned: Annotated[
        int | None,
        Field(description="Total desks scanned across all pages (full-walk modes)."),
    ] = None
    truncated: Annotated[
        bool | None,
        Field(
            description="True if the internal page cap was hit before the list was exhausted (full-walk modes)."
        ),
    ] = None
    venue: Annotated[
        str | None, Field(description="The venue filter applied, echoed when filtering by venue.")
    ] = None
    note: Annotated[
        str | None,
        Field(
            description="Set when `prime_only` was requested but no desk carried a prime signal."
        ),
    ] = None


Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
BaseCurrency = Literal["AVAX", "BCH", "BTC", "ETH", "SOL", "TONCOIN", "TRX", "XRP"]
InstrumentKind = Literal["FUTURE", "OPTION"]
MarginKind = Literal["INVERSE", "LINEAR"]
InstrumentState = Literal["ACTIVE", "EXPIRED"]

# Safety bound on the venue-filter page walk so a misbehaving cursor can
# never loop forever; the result reports `truncated` if this cap is hit.
_MAX_COUNTERPARTY_PAGES = 100


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


def _venue_codes(value: Any) -> list[str]:
    """Normalize a venues-style field into a list of upper-cased codes.

    Accepts the same two shapes as ``_desk_supports_venue``: bare strings
    or ``{name|venue|code}`` objects.
    """
    if not isinstance(value, list):
        return []
    codes: list[str] = []
    for entry in value:
        if isinstance(entry, str):
            name: Any = entry
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("venue") or entry.get("code")
        else:
            name = None
        if name is not None:
            codes.append(str(name).upper())
    return codes


def _groups_mark_prime(groups: Any) -> bool | None:
    """Whether a ``groups`` list contains an entry marking the desk prime.

    Returns ``True`` on a prime marker, ``False`` if groups is a list with
    no marker, and ``None`` when ``groups`` isn't a list (no signal).
    """
    if not isinstance(groups, list):
        return None
    for entry in groups:
        if isinstance(entry, str):
            label: Any = entry
        elif isinstance(entry, dict):
            label = entry.get("name") or entry.get("code") or entry.get("group")
        else:
            label = None
        if label is not None and "prime" in str(label).lower():
            return True
    return False


def _desk_prime_venue_enabled(desk: Any, venue: str | None = None) -> bool | None:
    """Whether a counterparty desk is a prime LP (for ``venue`` if given).

    The counterparties payload documents ``desk_name``/``firm_name``/
    ``groups``/``id``/``venues`` and carries no first-class ``prime``
    field, so we look — defensively, in order — at the places prime status
    could plausibly live, and return ``None`` when *none* of them is
    present so the caller can tell "not prime" apart from "the backend
    doesn't expose prime info". Candidate locations:

    - an explicit prime-venue list (``prime_venues``) — membership-checked
      against ``venue`` when given;
    - a top-level boolean (``prime`` / ``is_prime`` / ``prime_enabled`` /
      ``prime_venue_enabled``);
    - a ``groups`` entry whose name/code marks the desk as prime.

    The exact field is confirmed against the live testnet payload; adjust
    the candidate keys here if it differs.
    """
    if not isinstance(desk, dict):
        return None

    # 1) Explicit prime-venue list.
    if "prime_venues" in desk:
        codes = _venue_codes(desk.get("prime_venues"))
        if venue is not None:
            return venue.upper() in codes
        return bool(codes)

    # 2) Top-level boolean flag.
    for key in ("prime_venue_enabled", "prime_enabled", "is_prime", "prime"):
        if key in desk:
            return bool(desk.get(key))

    # 3) Prime marker inside `groups` (None when groups isn't present).
    return _groups_mark_prime(desk.get("groups"))


def _annotate_prime(desk: Any, venue: str | None) -> Any:
    """Return a shallow copy of ``desk`` with a ``prime_venue_enabled`` flag.

    Never mutates the upstream dict. Non-dict entries pass through.
    """
    if not isinstance(desk, dict):
        return desk
    return {**desk, "prime_venue_enabled": _desk_prime_venue_enabled(desk, venue)}


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


def _page_envelope(resp: Any) -> dict[str, Any]:
    """Normalize one upstream list page into a stable pagination contract.

    The raw DRF response exposes ``next`` as a full URL the MCP client
    can't reuse and has no ``has_more``; this returns
    ``{results, count, next_cursor, has_more, total}`` so the caller has
    an explicit, reusable cursor contract.
    """
    items = _list_items(resp)
    next_cursor = _next_cursor(resp)
    total = resp.get("count") if isinstance(resp, dict) else None
    if not isinstance(total, int):
        total = None
    return {
        "results": items,
        "count": len(items),
        "next_cursor": next_cursor,
        "has_more": bool(next_cursor),
        "total": total,
    }


async def _collect_all(
    client: ParadigmClient,
    *,
    predicate: Callable[[Any], bool] | None = None,
    cursor: str | None = None,
    page_size: int | None = None,
    max_pages: int = _MAX_COUNTERPARTY_PAGES,
) -> dict[str, Any]:
    """Walk every counterparties page, optionally filtering with ``predicate``.

    Bounded by ``max_pages`` so a misbehaving cursor can't loop forever;
    the result reports ``truncated`` if that cap is hit before the list is
    exhausted.
    """
    matched: list[Any] = []
    scanned = 0
    page_cursor = cursor
    truncated = True
    for _ in range(max_pages):
        resp = await client.get(
            "/v2/drfq/counterparties/",
            cursor=page_cursor,
            page_size=page_size,
        )
        items = _list_items(resp)
        scanned += len(items)
        matched.extend(d for d in items if predicate is None or predicate(d))
        page_cursor = _next_cursor(resp)
        if not page_cursor:
            truncated = False  # reached the last page → result is complete
            break
    return {
        "results": matched,
        "count": len(matched),
        "scanned": scanned,
        "truncated": truncated,
    }


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
    prime_only: Annotated[
        bool,
        Field(
            description=(
                "Return only prime-venue-enabled desks (combined with "
                "`venue` when both are set). Pages through every desk."
            )
        ),
    ] = False,
    fetch_all: Annotated[
        bool,
        Field(
            description=(
                "Page through every desk and return the complete set "
                "instead of a single page. Implied by `venue`/`prime_only`."
            )
        ),
    ] = False,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> CounterpartiesResult:
    """List counterparty desks the firm can RFQ.

    Each desk exposes ``desk_name``, ``firm_name``, ``groups``, ``id`` and
    ``venues`` — the settlement venues that desk can trade. Use the
    ``venues`` field (or the ``venue`` filter) to resolve which LPs can
    quote a given venue before calling ``paradigm_drfqv2_create_rfq``;
    a desk that doesn't list a venue can't be quoted there.

    Pagination contract:

    - Default (no ``venue``/``prime_only``/``fetch_all``) returns one page
      as ``{"results", "count", "next_cursor", "has_more", "total"}`` —
      pass ``next_cursor`` back as ``cursor`` to page. (``next_cursor`` is
      an opaque token; the raw DRF full-URL ``next`` is not reusable and
      is intentionally not surfaced.)
    - ``fetch_all=true`` (or ``venue``/``prime_only``) pages through every
      desk and returns the complete set as
      ``{"results", "count", "scanned", "truncated"}`` (plus ``"venue"``
      when filtering by venue). ``truncated`` is true only if the internal
      page cap was hit before the list was exhausted.

    Each returned desk is annotated with ``prime_venue_enabled``: ``true``/
    ``false`` when the payload carries a prime signal, ``null`` when the
    backend doesn't expose one (so prime is never *inferred*). If
    ``prime_only`` is requested but no desk carries any prime signal, the
    result includes a ``"note"`` saying so rather than silently returning
    an empty list.
    """
    client = await get_paradigm_client()

    walk = fetch_all or venue is not None or prime_only

    if not walk:
        envelope = _page_envelope(
            await client.get("/v2/drfq/counterparties/", cursor=cursor, page_size=page_size)
        )
        envelope["results"] = [_annotate_prime(d, venue) for d in envelope["results"]]
        return envelope

    # Walk filtering only on venue; prime is applied afterward so we can
    # tell "no prime desks" from "backend exposes no prime signal".
    venue_predicate = (lambda d: _desk_supports_venue(d, venue)) if venue is not None else None
    result = await _collect_all(
        client, predicate=venue_predicate, cursor=cursor, page_size=page_size
    )

    desks = result["results"]
    prime_states = [_desk_prime_venue_enabled(d, venue) for d in desks]
    any_prime_signal = any(state is not None for state in prime_states)

    if prime_only:
        desks = [d for d, state in zip(desks, prime_states, strict=True) if state]
    result["results"] = [_annotate_prime(d, venue) for d in desks]
    result["count"] = len(result["results"])
    if venue is not None:
        result["venue"] = venue
    if prime_only and not result["results"] and not any_prime_signal:
        result["note"] = (
            "No desk in the counterparties payload carries a prime-venue "
            "signal; the backend may not expose prime info yet."
        )
    return result
