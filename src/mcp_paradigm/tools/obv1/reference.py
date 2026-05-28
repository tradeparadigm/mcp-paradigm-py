"""OBv1 reference data: instruments + platform state."""

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
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    asset: Annotated[Asset | None, Field(description="BCH, BTC, or ETH.")] = None,
    kind: Annotated[Kind | None, Field(description="FUTURE or OPTION.")] = None,
    name: Annotated[list[str] | None, Field(description="Venue-native names.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List OBv1 instruments tradable on Paradigm."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/instruments/",
        venue=venue,
        asset=asset,
        kind=kind,
        name=name,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_obv1_instrument",
    title="OBv1 Instrument",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_instrument(
    venue: Annotated[str, Field(description="Venue code (e.g. DBT).")],
    name: Annotated[str, Field(description="Venue instrument name (e.g. BTC-15MAY24-64500-C).")],
) -> Any:
    """Fetch a single OBv1 instrument by (venue, name)."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/instruments/{venue}/{name}/")


@server.tool(
    name="paradigm_obv1_platform_state",
    title="OBv1 Platform State",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_platform_state() -> Any:
    """Current and next OBv1 platform state."""
    client = await get_paradigm_client()
    return await client.get("/v1/ob/platform_state/")
