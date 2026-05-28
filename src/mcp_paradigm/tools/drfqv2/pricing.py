"""DRFQv2 leg pricing."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.paradigm_client import get_paradigm_client

Side = Literal["BUY", "SELL"]


class PricingLeg(BaseModel):
    instrument_id: int = Field(description="Paradigm instrument id.")
    ratio: str = Field(description="Leg ratio (decimal string).")
    side: Side = Field(description="BUY or SELL.")


@server.tool(
    name="paradigm_drfqv2_price_legs",
    title="DRFQv2 Price Legs",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_price_legs(
    legs: Annotated[list[PricingLeg], Field(description="Strategy legs.", min_length=1)],
    bid_price: Annotated[str | None, Field(description="Strategy-level bid.")] = None,
    ask_price: Annotated[str | None, Field(description="Strategy-level ask.")] = None,
    accept_estimated_prices: Annotated[
        bool | None, Field(description="Accept estimated prices.")
    ] = None,
    algorithm_version: Annotated[str | None, Field(description="Algorithm version.")] = None,
) -> Any:
    """Given strategy bid/ask, return per-leg prices."""
    client = await get_paradigm_client()
    body: dict[str, Any] = {"legs": [leg.model_dump() for leg in legs]}
    if bid_price is not None:
        body["bid_price"] = bid_price
    if ask_price is not None:
        body["ask_price"] = ask_price
    if accept_estimated_prices is not None:
        body["accept_estimated_prices"] = accept_estimated_prices
    if algorithm_version is not None:
        body["algorithm_version"] = algorithm_version
    return await client.post("/v2/drfq/pricing/", json_body=body)
