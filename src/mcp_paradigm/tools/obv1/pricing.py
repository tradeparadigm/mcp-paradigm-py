"""OBv1 leg pricing."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Side = Literal["BUY", "SELL"]
Venue = Literal["BYB", "DBT", "BIT", "PRDX"]


class PricingLeg(BaseModel):
    instrument: str = Field(description="Venue-native instrument name.")
    ratio: str = Field(description="Leg ratio (decimal).")
    side: Side = Field(description="BUY or SELL.")


@server.tool(
    name="paradigm_obv1_price_legs",
    title="OBv1 Price Legs",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_price_legs(
    venue: Annotated[Venue, Field(description="Pricing venue.")],
    legs: Annotated[list[PricingLeg], Field(description="Strategy legs.", min_length=1)],
    bid_price: Annotated[str | None, Field(description="Strategy bid (decimal).")] = None,
    ask_price: Annotated[str | None, Field(description="Strategy ask (decimal).")] = None,
    accept_estimated_prices: Annotated[
        bool | None, Field(description="Allow estimated prices.")
    ] = None,
    algorithm_version: Annotated[
        str | None, Field(description="Pricing algorithm version.")
    ] = None,
) -> Any:
    """Given strategy bid/ask, return per-leg prices."""
    client = await get_paradigm_client()
    body: dict[str, Any] = {
        "venue": venue,
        "legs": [leg.model_dump() for leg in legs],
    }
    if bid_price is not None:
        body["bid_price"] = bid_price
    if ask_price is not None:
        body["ask_price"] = ask_price
    if accept_estimated_prices is not None:
        body["accept_estimated_prices"] = accept_estimated_prices
    if algorithm_version is not None:
        body["algorithm_version"] = algorithm_version
    return await client.post("/v1/ob/pricing/", json_body=body)
