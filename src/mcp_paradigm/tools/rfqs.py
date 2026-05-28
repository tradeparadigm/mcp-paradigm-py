"""RFQ lifecycle tools (taker side)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Venue = Literal["BIT", "BYB", "DBT", "PRDX", "RBN", "TTN", "BLT", "FBX", "FKN", "FTX", "SKD", "CME"]
RFQState = Literal["RFQState.OPEN", "RFQState.CLOSED", "RFQState.DRAFT"]
Role = Literal["AuctionRole.MAKER", "AuctionRole.TAKER"]
Side = Literal["BUY", "SELL"]


class LegCreate(BaseModel):
    instrument_id: int = Field(description="Paradigm instrument id.")
    ratio: str = Field(description="Leg ratio (decimal string).")
    side: Side = Field(description="BUY or SELL.")
    price: str | None = Field(default=None, description="Optional indicative leg price.")


@server.tool(
    name="paradigm_rfqs",
    title="RFQs",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_rfqs(
    state: Annotated[RFQState | None, Field(description="Filter by RFQ state.")] = None,
    role: Annotated[Role | None, Field(description="MAKER or TAKER perspective.")] = None,
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy code filter.")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List RFQs visible to the desk."""
    client = await get_paradigm_client()
    return await client.get(
        "/v2/drfq/rfqs/",
        state=state,
        role=role,
        venue=venue,
        strategies=strategies,
        product_codes=product_codes,
        cursor=cursor,
        page_size=page_size,
    )


@server.tool(
    name="paradigm_rfq",
    title="RFQ",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_rfq(
    rfq_id: Annotated[str, Field(description="Paradigm RFQ id.")],
) -> Any:
    """Fetch a single RFQ."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/rfqs/{rfq_id}/")


@server.tool(
    name="paradigm_rfq_bbo",
    title="RFQ BBO",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_rfq_bbo(
    rfq_id: Annotated[str, Field(description="Paradigm RFQ id.")],
) -> Any:
    """Best bid/offer for an RFQ — mark, min/max price, greeks, per-leg bbo."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/rfqs/{rfq_id}/bbo/")


@server.tool(
    name="paradigm_rfq_orders",
    title="RFQ Order Book",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_rfq_orders(
    rfq_id: Annotated[str, Field(description="Paradigm RFQ id.")],
) -> Any:
    """Order book against an RFQ: asks[] and bids[] with price/quantity/desk."""
    client = await get_paradigm_client()
    return await client.get(f"/v2/drfq/rfqs/{rfq_id}/orders/")


@server.tool(
    name="paradigm_create_rfq",
    title="Create RFQ",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False),
)
async def paradigm_create_rfq(
    venue: Annotated[Venue, Field(description="Settlement venue.")],
    legs: Annotated[list[LegCreate], Field(description="Strategy legs.", min_length=1)],
    quantity: Annotated[str, Field(description="RFQ quantity (decimal string).")],
    counterparties: Annotated[
        list[str], Field(description="Desk names to RFQ. Empty list = all eligible.")
    ],
    is_taker_anonymous: Annotated[
        bool, Field(description="Hide the taker desk name from counterparties.")
    ] = True,
    account_name: Annotated[
        str | None, Field(description="Account to bill (omit for desk default).")
    ] = None,
    label: Annotated[
        str | None, Field(description="Caller idempotency label, echoed in response.", max_length=128)
    ] = None,
    state: Annotated[
        Literal["RFQState.OPEN", "RFQState.DRAFT"],
        Field(description="OPEN sends now; DRAFT stages without notifying counterparties."),
    ] = "RFQState.OPEN",
) -> Any:
    """Create a new RFQ. Returns the RFQ entity including ``id``.

    This places a request-for-quote on the wire to the chosen
    counterparties — gate behind explicit user confirmation.
    """
    client = await get_paradigm_client()
    body: dict[str, Any] = {
        "venue": venue,
        "legs": [leg.model_dump(exclude_none=True) for leg in legs],
        "quantity": quantity,
        "counterparties": counterparties,
        "is_taker_anonymous": is_taker_anonymous,
        "state": state,
    }
    if account_name is not None:
        body["account_name"] = account_name
    if label is not None:
        body["label"] = label
    return await client.post("/v2/drfq/rfqs/", json_body=body)


@server.tool(
    name="paradigm_cancel_rfq",
    title="Cancel RFQ",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_cancel_rfq(
    rfq_id: Annotated[str, Field(description="Paradigm RFQ id.")],
) -> dict[str, Any]:
    """Cancel an open RFQ before expiry."""
    client = await get_paradigm_client()
    await client.delete(f"/v2/drfq/rfqs/{rfq_id}/")
    return {"rfq_id": rfq_id, "canceled": True}
