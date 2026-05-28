"""DRFQv2 RFQ lifecycle. Single-fetch is via ``paradigm_drfqv2_rfq_snapshot``."""

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
    name="paradigm_drfqv2_rfqs",
    title="DRFQv2 RFQs",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_rfqs(
    state: Annotated[RFQState | None, Field(description="Filter by RFQ state.")] = None,
    role: Annotated[Role | None, Field(description="MAKER or TAKER perspective.")] = None,
    venue: Annotated[Venue | None, Field(description="Filter by venue.")] = None,
    strategies: Annotated[str | None, Field(description="Strategy code filter.")] = None,
    product_codes: Annotated[str | None, Field(description="Product code filter.")] = None,
    cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
    page_size: Annotated[int | None, Field(description="Page size.", ge=1, le=1000)] = None,
) -> Any:
    """List DRFQv2 RFQs visible to the desk.

    For a single RFQ with its BBO and order book, use
    ``paradigm_drfqv2_rfq_snapshot`` instead.
    """
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
    name="paradigm_drfqv2_create_rfq",
    title="DRFQv2 Create RFQ",
    annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False),
)
async def paradigm_drfqv2_create_rfq(
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
        str | None,
        Field(description="Caller idempotency label, echoed in response.", max_length=128),
    ] = None,
    state: Annotated[
        Literal["RFQState.OPEN", "RFQState.DRAFT"],
        Field(description="OPEN sends now; DRAFT stages without notifying counterparties."),
    ] = "RFQState.OPEN",
) -> Any:
    """Create a new DRFQv2 RFQ to the chosen counterparties.

    Places a request-for-quote on the wire — gate behind explicit user
    confirmation.
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
