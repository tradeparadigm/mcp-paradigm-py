"""Cross-product workflow tools — desk health and kill switch.

These compose multiple per-product calls into single high-value tools
that answer the question an agent actually has ("am I healthy?", "stop
everything"), rather than forcing the agent to orchestrate.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

import httpx
from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_paradigm.server.server import server
from mcp_paradigm.utils.errors import ParadigmAPIError
from mcp_paradigm.utils.paradigm_client import get_fspd_client, get_paradigm_client


async def _safe(coro: Any, timeout: float = 8.0) -> Any:
    """Run a coroutine with a per-call timeout, return its result or a
    structured error envelope on failure.

    The timeout bounds workflow tools so one slow product doesn't block
    the rest (``paradigm_desk_overview``'s gathered calls would otherwise
    wait for the slowest up to the global request timeout).

    Error envelope shape (from ``ParadigmAPIError.to_dict``)::

        {
          "error_type": "ParadigmValidationError",
          "status_code": 422,
          "method": "POST",
          "path": "/v2/drfq/orders/",
          "request_id": "...",
          "body": {...},
          "message": "422 POST /v2/drfq/orders/ | validation_failed: ... | hint: ...",
          "hint": "Read `data` for per-field errors..."
        }
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except (TimeoutError, httpx.TimeoutException):
        return _envelope(
            "TimeoutError",
            f"timeout after {timeout}s",
            "The endpoint exceeded the workflow tool's per-call budget — call the per-product tool directly to confirm whether it's degraded.",
        )
    except ParadigmAPIError as exc:
        return exc.to_dict()
    except httpx.HTTPError as exc:
        # Connection refused, DNS failure, TLS error, etc. — httpx exceptions
        # often stringify empty, so include the class name for visibility.
        return _envelope(
            type(exc).__name__,
            f"{type(exc).__name__}: {exc!s}" if str(exc) else type(exc).__name__,
            "Network-level failure reaching Paradigm — verify PARADIGM_BASE_URL / PARADIGM_FSPD_BASE_URL and outbound connectivity.",
        )
    except Exception as exc:  # pragma: no cover
        return _envelope(type(exc).__name__, str(exc) or type(exc).__name__, None)


def _envelope(error_type: str, message: str, hint: str | None) -> dict[str, Any]:
    """Same shape as ``ParadigmAPIError.to_dict`` so the agent sees one
    error envelope regardless of which failure mode tripped."""
    return {
        "error_type": error_type,
        "status_code": None,
        "method": None,
        "path": None,
        "request_id": None,
        "body": None,
        "message": message,
        "hint": hint,
    }


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
    if not (drfqv2 or obv1 or fspd):
        raise ValueError(
            "paradigm_kill_switch: no products selected (drfqv2/obv1/fspd all False). "
            "Pass at least one product=True; defaults are True for all three."
        )
    drfq = await get_paradigm_client()
    fspd_client = await get_fspd_client()

    tasks: dict[str, Any] = {}
    if drfqv2:
        tasks["drfqv2_orders"] = drfq.delete("/v2/drfq/orders/")
    if obv1:
        tasks["obv1_quotes"] = drfq.delete("/v1/ob/quotes/")
    if fspd:
        tasks["fspd_orders"] = fspd_client.delete("/v1/fs/orders")

    # Fan out — every second a stuck product holds liquidity is a
    # second too long. Use a wider timeout than the snapshot tools.
    names = list(tasks.keys())
    outcomes = await asyncio.gather(*(_safe(tasks[n], timeout=20.0) for n in names))
    return dict(zip(names, outcomes, strict=True))


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
