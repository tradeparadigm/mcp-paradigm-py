"""Live testnet integration evals — skipped unless credentials are set.

These exercise the real Paradigm API and are the only tests that touch
the network. They are gated two ways:

- The whole module is marked ``integration`` and skips unless
  ``PARADIGM_ACCESS_KEY`` + ``PARADIGM_SIGNING_KEY`` are present, so the
  default ``pytest`` run (and CI, which has no creds) skips them.
- The write-path eval (which puts an RFQ on the wire) additionally
  requires ``PARADIGM_INTEGRATION_WRITES=1`` plus an operator-supplied,
  known-safe instrument, so it never fires by accident.

Run against testnet with::

    export PARADIGM_ENVIRONMENT=testnet
    export PARADIGM_ACCESS_KEY=... PARADIGM_SIGNING_KEY=...
    pytest -m integration

They primarily de-risk the WebSocket surface — the handshake auth and
the exact channel names — which the unit tests can only fake.
"""

from __future__ import annotations

import os

import pytest

from mcp_paradigm.utils.ws_manager import CHANNELS, WSManager

_HAVE_CREDS = bool(os.getenv("PARADIGM_ACCESS_KEY") and os.getenv("PARADIGM_SIGNING_KEY"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _HAVE_CREDS,
        reason="set PARADIGM_ACCESS_KEY + PARADIGM_SIGNING_KEY to run live testnet tests",
    ),
]


async def _client():
    # Import lazily so collection doesn't construct a client when skipped.
    from mcp_paradigm.utils.paradigm_client import ParadigmClient

    return ParadigmClient()


@pytest.mark.asyncio
async def test_echo_round_trip() -> None:
    """Signing + auth are wired up end-to-end."""
    client = await _client()
    try:
        result = await client.get("/v2/drfq/echo/")
    finally:
        await client.close()
    assert result is not None


@pytest.mark.asyncio
async def test_counterparties_expose_venues() -> None:
    """Each desk carries the `venues` field the venue filter relies on."""
    client = await _client()
    try:
        resp = await client.get("/v2/drfq/counterparties/", page_size=50)
    finally:
        await client.close()
    items = resp.get("results", resp) if isinstance(resp, dict) else resp
    assert isinstance(items, list)
    if items:  # an empty counterparty list is a valid (if quiet) account
        assert any("venues" in d for d in items if isinstance(d, dict)), (
            "no desk exposed a `venues` field — the venue filter assumption is wrong"
        )


@pytest.mark.asyncio
async def test_counterparties_pagination_contract() -> None:
    """The unfiltered tool path returns the normalized cursor contract."""
    from mcp_paradigm.tools.drfqv2 import reference

    out = await reference.paradigm_drfqv2_counterparties(page_size=5)
    assert isinstance(out, dict)
    for key in ("results", "count", "next_cursor", "has_more", "total"):
        assert key in out, f"pagination contract missing `{key}`: {out.keys()}"
    assert isinstance(out["results"], list)


@pytest.mark.asyncio
async def test_counterparties_prime_signal_probe() -> None:
    """Surface whether the live payload carries any prime-venue signal.

    Items 2's prime filter only works if the backend exposes prime info.
    This walks the desks and checks ``_desk_prime_venue_enabled``; if no
    desk carries a signal it *skips* with a message that documents the
    finding (the backend ask) rather than failing.
    """
    from mcp_paradigm.tools.drfqv2 import reference

    out = await reference.paradigm_drfqv2_counterparties(fetch_all=True)
    desks = out["results"]
    states = [d.get("prime_venue_enabled") for d in desks if isinstance(d, dict)]
    if not any(s is not None for s in states):
        pytest.skip(
            "no desk carries a prime-venue signal — the counterparties "
            "payload does not expose prime info; prime_only is a documented "
            "no-op until the backend adds it (see _desk_prime_venue_enabled)."
        )
    # If a signal exists, the filter must agree with the annotation.
    prime = await reference.paradigm_drfqv2_counterparties(prime_only=True)
    assert all(d.get("prime_venue_enabled") for d in prime["results"])


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", CHANNELS)
async def test_websocket_subscribe_poll_unsubscribe(channel: str) -> None:
    """The live socket accepts each documented channel.

    This is the eval that would catch a wrong channel name (e.g. `order`
    vs `quote`) or a broken handshake — the unit tests can only assert
    the manager's logic against a fake connection.
    """
    manager = WSManager()
    sub = await manager.subscribe(channel)
    try:
        assert sub["subscription_id"]
        out = await manager.poll(sub["subscription_id"])
        # The socket should be live after a successful subscribe; events
        # may legitimately be empty on a quiet channel.
        assert out["connected"] is True
        assert out["channel"] == channel
    finally:
        await manager.unsubscribe(sub["subscription_id"])


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("PARADIGM_INTEGRATION_WRITES") != "1",
    reason="write-path eval is opt-in: set PARADIGM_INTEGRATION_WRITES=1 + a known-safe instrument",
)
async def test_create_rfq_broadcast_then_cancel() -> None:
    """Empty `counterparties` is accepted as a broadcast, then cleaned up.

    Requires operator-supplied, known-safe inputs so it never guesses an
    instrument:
      PARADIGM_TEST_VENUE, PARADIGM_TEST_INSTRUMENT_ID,
      PARADIGM_TEST_RATIO (default "1"), PARADIGM_TEST_QUANTITY.
    """
    venue = os.environ["PARADIGM_TEST_VENUE"]
    instrument_id = int(os.environ["PARADIGM_TEST_INSTRUMENT_ID"])
    ratio = os.getenv("PARADIGM_TEST_RATIO", "1")
    quantity = os.environ["PARADIGM_TEST_QUANTITY"]

    client = await _client()
    rfq_id = None
    try:
        created = await client.post(
            "/v2/drfq/rfqs/",
            json_body={
                "venue": venue,
                "legs": [{"instrument_id": instrument_id, "ratio": ratio, "side": "BUY"}],
                "quantity": quantity,
                "counterparties": [],  # broadcast to all venue-eligible makers
                "is_taker_anonymous": True,
                "state": "OPEN",
            },
        )
        rfq_id = created.get("id") if isinstance(created, dict) else None
        assert rfq_id, f"create_rfq did not return an id: {created!r}"
    finally:
        if rfq_id is not None:
            await client.delete(f"/v2/drfq/rfqs/{rfq_id}/")
        await client.close()
