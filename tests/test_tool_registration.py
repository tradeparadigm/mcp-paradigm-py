"""Guard the registered tool surface against silent drift.

The README and DESIGN.md advertise an exact tool count and name the
streaming tools by hand; this test fails if the registry and the docs
fall out of sync (as they had — the docs said "39" while 40 were
registered). Update the count here *and* in README.md / DESIGN.md in the
same change.
"""

from __future__ import annotations

import pytest

from mcp_paradigm.server.server import server

# Keep in lockstep with the "N tools total" line in DESIGN.md and the
# "N tools, workflow-oriented" line in README.md.
EXPECTED_TOOL_COUNT = 43

STREAMING_TOOLS = {"paradigm_subscribe", "paradigm_poll", "paradigm_unsubscribe"}


@pytest.mark.asyncio
async def test_tool_count_matches_docs() -> None:
    tools = await server.list_tools()
    assert len(tools) == EXPECTED_TOOL_COUNT, (
        f"registered {len(tools)} tools but docs claim {EXPECTED_TOOL_COUNT}; "
        "update EXPECTED_TOOL_COUNT here and the counts in README.md + DESIGN.md."
    )


@pytest.mark.asyncio
async def test_streaming_tools_are_registered() -> None:
    names = {t.name for t in await server.list_tools()}
    missing = STREAMING_TOOLS - names
    assert not missing, f"streaming tools not registered: {missing}"


@pytest.mark.asyncio
async def test_counterparties_exposes_venue_filter() -> None:
    tools = {t.name: t for t in await server.list_tools()}
    props = tools["paradigm_drfqv2_counterparties"].inputSchema["properties"]
    assert "venue" in props, "counterparties must expose a `venue` filter"
    assert "prime_only" in props, "counterparties must expose a `prime_only` filter"
    assert "fetch_all" in props, "counterparties must expose a `fetch_all` flag"


@pytest.mark.asyncio
async def test_owned_envelopes_expose_output_schema() -> None:
    """Tools returning a shape the server owns advertise a structured outputSchema."""
    tools = {t.name: t for t in await server.list_tools()}
    expected = {
        "paradigm_drfqv2_counterparties": {"results", "count", "next_cursor", "has_more"},
        "paradigm_poll": {"subscription_id", "channel", "events", "cursor", "connected"},
        "paradigm_subscribe": {"subscription_id", "channel"},
        "paradigm_unsubscribe": {"subscription_id", "channel", "closed"},
    }
    for name, must_have in expected.items():
        schema = tools[name].outputSchema
        assert schema is not None, f"{name} should advertise an outputSchema"
        props = set(schema.get("properties", {}))
        assert must_have <= props, f"{name} outputSchema missing {must_have - props}"


@pytest.mark.asyncio
async def test_create_rfq_counterparties_optional_with_broadcast_default() -> None:
    tools = {t.name: t for t in await server.list_tools()}
    schema = tools["paradigm_drfqv2_create_rfq"].inputSchema
    assert "counterparties" not in schema.get("required", [])
    assert schema["properties"]["counterparties"].get("default") == []
