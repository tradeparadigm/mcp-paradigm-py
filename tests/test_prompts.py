"""Tests for the MCP prompt templates.

Assert the prompts register, render with sample args, name the real tools
they orchestrate, and that their optional arguments are genuinely optional
(can be omitted).
"""

from __future__ import annotations

import pytest

from mcp_paradigm.server.server import server

EXPECTED_PROMPTS = {"quote_rfq", "broadcast_rfq", "stream_and_tail"}


def _text(result) -> str:
    """Concatenate the text of a GetPromptResult's messages."""
    parts = []
    for msg in result.messages:
        content = msg.content
        parts.append(content.text if hasattr(content, "text") else str(content))
    return "\n".join(parts)


@pytest.mark.asyncio
async def test_prompts_are_registered() -> None:
    names = {p.name for p in await server.list_prompts()}
    assert names >= EXPECTED_PROMPTS, f"missing prompts: {EXPECTED_PROMPTS - names}"


@pytest.mark.asyncio
async def test_quote_rfq_names_maker_tools() -> None:
    out = await server.get_prompt("quote_rfq", {"rfq_id": "rfq_123"})
    text = _text(out)
    assert "rfq_123" in text
    for tool in ("paradigm_drfqv2_rfq_snapshot", "paradigm_drfqv2_post_order"):
        assert tool in text


@pytest.mark.asyncio
async def test_broadcast_rfq_documents_empty_counterparties() -> None:
    out = await server.get_prompt("broadcast_rfq", {"venue": "PRDX"})
    text = _text(out)
    assert "paradigm_drfqv2_create_rfq" in text
    assert "counterparties=[]" in text  # the broadcast default is spelled out


@pytest.mark.asyncio
async def test_optional_args_can_be_omitted() -> None:
    """broadcast_rfq.base_currency and stream_and_tail.channel are optional."""
    # base_currency omitted — must still render.
    bcast = await server.get_prompt("broadcast_rfq", {"venue": "DBT"})
    assert "DBT" in _text(bcast)

    # channel omitted — defaults to rfq.
    stream = await server.get_prompt("stream_and_tail", {})
    text = _text(stream)
    for tool in ("paradigm_subscribe", "paradigm_poll", "paradigm_unsubscribe"):
        assert tool in text
