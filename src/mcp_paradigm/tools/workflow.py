"""Cross-product workflow tools — desk health and kill switch.

These compose multiple per-product calls into single high-value tools
that answer the question an agent actually has ("am I healthy?", "stop
everything"), rather than forcing the agent to orchestrate.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.errors import ParadigmAPIError
from mcp_paradigm.utils.paradigm_client import get_fspd_client, get_paradigm_client


async def _safe(coro: Any) -> Any:
    """Run a coroutine, return its result or ``{'error': str}`` on failure."""
    try:
        return await coro
    except ParadigmAPIError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc)}


@server.tool(
    name="paradigm_desk_overview",
    title="Desk Overview",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_desk_overview() -> dict[str, Any]:
    """One-shot snapshot of desk health across all active Paradigm products.

    Combines: positions, identity credentials, MMP status (DRFQv2,
    OBv1, FSPD), and per-product platform / system state. Use this as
    the first call to answer "what state is my desk in?" before drilling
    into specific products.
    """
    drfq = await get_paradigm_client()
    fspd = await get_fspd_client()

    (
        positions,
        credentials,
        mmp_drfqv2,
        mmp_obv1,
        mmp_fspd,
        platform_drfqv2,
        platform_obv1,
        fspd_state,
        fspd_time,
    ) = await asyncio.gather(
        _safe(drfq.get("/v1/positions/")),
        _safe(drfq.get("/v1/identity/credentials/")),
        _safe(drfq.get("/v2/drfq/mmp/status/")),
        _safe(drfq.get("/v1/ob/mmp/status/")),
        _safe(fspd.get("/v1/fs/mmp/status")),
        _safe(drfq.get("/v2/drfq/platform_state/")),
        _safe(drfq.get("/v1/ob/platform_state/")),
        _safe(fspd.get("/v1/fs/system/state")),
        _safe(fspd.get("/v1/fs/system/time")),
    )
    return {
        "positions": positions,
        "credentials": credentials,
        "mmp": {"drfqv2": mmp_drfqv2, "obv1": mmp_obv1, "fspd": mmp_fspd},
        "platform": {
            "drfqv2": platform_drfqv2,
            "obv1": platform_obv1,
            "fspd": {"state": fspd_state, "time": fspd_time},
        },
    }


@server.tool(
    name="paradigm_kill_switch",
    title="Kill Switch (Cancel All)",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True),
)
async def paradigm_kill_switch(
    drfqv2: Annotated[bool, Field(description="Cancel all DRFQv2 orders.")] = True,
    obv1: Annotated[bool, Field(description="Cancel all OBv1 quotes.")] = True,
    fspd: Annotated[bool, Field(description="Cancel all FSPD orders.")] = True,
) -> dict[str, Any]:
    """Cancel everything live across the desk in a single call.

    DESTRUCTIVE. Use as a kill switch when something's gone wrong or
    end-of-day shutdown. By default cancels DRFQv2 orders, OBv1 quotes,
    and FSPD orders. Disable any product with ``<product>=False``.

    RFQs/OBs you created stay open — only your active orders and quotes
    are pulled.
    """
    drfq = await get_paradigm_client()
    fspd_client = await get_fspd_client()

    tasks: dict[str, Any] = {}
    if drfqv2:
        tasks["drfqv2_orders"] = drfq.delete("/v2/drfq/orders/")
    if obv1:
        tasks["obv1_quotes"] = drfq.delete("/v1/ob/quotes/")
    if fspd:
        tasks["fspd_orders"] = fspd_client.delete("/v1/fs/orders")

    results: dict[str, Any] = {}
    for name, coro in tasks.items():
        results[name] = await _safe(coro)
    return results


@server.tool(
    name="paradigm_drfqv2_rfq_snapshot",
    title="DRFQv2 RFQ Snapshot",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_drfqv2_rfq_snapshot(
    rfq_id: Annotated[str, Field(description="Paradigm DRFQv2 RFQ id.")],
) -> dict[str, Any]:
    """Full state of a DRFQv2 RFQ in one call: RFQ + BBO + order book."""
    client = await get_paradigm_client()
    rfq, bbo, orders = await asyncio.gather(
        _safe(client.get(f"/v2/drfq/rfqs/{rfq_id}/")),
        _safe(client.get(f"/v2/drfq/rfqs/{rfq_id}/bbo/")),
        _safe(client.get(f"/v2/drfq/rfqs/{rfq_id}/orders/")),
    )
    return {"rfq": rfq, "bbo": bbo, "orders": orders}


@server.tool(
    name="paradigm_obv1_market_snapshot",
    title="OBv1 Market Snapshot",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def paradigm_obv1_market_snapshot(
    ob_id: Annotated[str, Field(description="OBv1 market id.")],
) -> dict[str, Any]:
    """Full state of an OBv1 order book market: market + BBO + quotes book."""
    client = await get_paradigm_client()
    market, bbo, quotes = await asyncio.gather(
        _safe(client.get(f"/v1/ob/rfqs/{ob_id}/")),
        _safe(client.get(f"/v1/ob/rfqs/{ob_id}/bbo/")),
        _safe(client.get(f"/v1/ob/rfqs/{ob_id}/quotes/")),
    )
    return {"market": market, "bbo": bbo, "quotes": quotes}
