"""OBv1 reference data: instruments. Platform state lives in desk_overview."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX"]
Asset = Literal["BCH", "BTC", "ETH"]
Kind = Literal["FUTURE", "OPTION"]


@server.tool(
    name="paradigm_obv1_instruments",
    title="OBv1 Instruments",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_instruments(
    venue: Annotated[
        Venue | None, Field(description="If set with `instrument_name`, fetches one.")
    ] = None,
    instrument_name: Annotated[
        str | None,
        Field(
            description="If set with `venue`, fetches the single instrument by venue-native name."
        ),
    ] = None,
    asset: Annotated[Asset | None, Field(description="BCH, BTC, or ETH.")] = None,
    kind: Annotated[Kind | None, Field(description="FUTURE or OPTION.")] = None,
    name: Annotated[list[str] | None, Field(description="Venue-native names filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List OBv1 instruments, or fetch one by ``(venue, instrument_name)``."""
    client = await get_paradigm_client()
    if venue is not None and instrument_name is not None:
        return await client.get(f"/v1/ob/instruments/{venue}/{instrument_name}/")
    return await client.get(
        "/v1/ob/instruments/",
        venue=venue,
        asset=asset,
        kind=kind,
        name=name,
        cursor=cursor,
        page_size=page_size,
    )
