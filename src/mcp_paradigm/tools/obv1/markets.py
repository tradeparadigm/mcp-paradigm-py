"""OBv1 markets — long-lived public order book auctions ("OBs"/RFQs)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Side = Literal["BUY", "SELL"]
Venue = Literal["BIT", "BYB", "DBT", "PRDX", "RBN", "TTN", "BLT", "FBX", "FKN", "FTX", "SKD", "CME"]


class LegCreate(BaseModel):
    instrument: str = Field(description="Venue-native instrument name.")
    ratio: str = Field(description="Leg ratio (decimal string).")
    side: Side = Field(description="BUY or SELL.")
    price: str | None = Field(default=None, description="Optional indicative leg price.")


@server.tool(
    name="paradigm_obv1_obs",
    title="OBv1 Order Book Markets",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_obs(
    rfq_id: Annotated[str | None, Field(description="Filter by OB id.")] = None,
    strategies: Annotated[
        str | None, Field(description="Strategy codes (comma-separated).")
    ] = None,
    product_codes: Annotated[
        str | None, Field(description="Product codes (comma-separated).")
    ] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List active OBv1 order book markets, by latest_activity descending."""
    client = await get_paradigm_client()
    return await client.get(
        "/v1/ob/rfqs/",
        rfq_id=rfq_id,
        strategies=strategies,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_obv1_ob",
    title="OBv1 Market",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_ob(
    ob_id: Annotated[str, Field(description="OB id.")],
) -> Any:
    """Fetch a single OBv1 market by id."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/rfqs/{ob_id}/")


@server.tool(
    name="paradigm_obv1_bbo",
    title="OBv1 BBO",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_bbo(
    ob_id: Annotated[str, Field(description="OB id.")],
) -> Any:
    """Best bid/offer for an OBv1 market — mark, index, per-leg bbo, greeks."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/rfqs/{ob_id}/bbo/")


@server.tool(
    name="paradigm_obv1_ob_quotes",
    title="OBv1 Market Quotes",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_ob_quotes(
    ob_id: Annotated[str, Field(description="OB id.")],
) -> Any:
    """All active quotes on an OBv1 market — asks[]/bids[]."""
    client = await get_paradigm_client()
    return await client.get(f"/v1/ob/rfqs/{ob_id}/quotes/")


@server.tool(
    name="paradigm_obv1_create_ob",
    title="OBv1 Create Market",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False),
)
async def paradigm_obv1_create_ob(
    venue: Annotated[Venue, Field(description="Settlement venue.")],
    legs: Annotated[list[LegCreate], Field(description="Strategy legs.", min_length=1)],
) -> Any:
    """Create a new OBv1 order book market.

    Opens a public, multi-counterparty order book for the given
    strategy. Gate behind explicit user confirmation.
    """
    client = await get_paradigm_client()
    body = {
        "venue": venue,
        "legs": [leg.model_dump(exclude_none=True) for leg in legs],
    }
    return await client.post("/v1/ob/rfqs/", json_body=body)
