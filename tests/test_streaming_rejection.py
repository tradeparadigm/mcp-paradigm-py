"""Tests for structured rejection annotation on pushed WebSocket events.

Paradigm's DRFQ WebSocket has no dedicated error channel — rejections
arrive as state transitions on the ``trade``/``order`` channels. The
``paradigm_poll`` tool annotates such events with a structured
``rejection`` block so a pushed failure reads as a failure, mirroring the
REST path, rather than looking like "still waiting".
"""

from __future__ import annotations

from typing import Any

import pytest

from mcp_paradigm.tools.drfqv2 import streaming


def test_annotate_rejection_only_on_rejection_channels() -> None:
    # Rejected trade on the `trade` channel → annotated.
    ev = {"channel": "trade", "data": {"state": "REJECTED", "rejection_reason": "MMP"}}
    out = streaming._annotate_rejection(ev)
    assert out["rejection"]["reason"] == "MMP"

    # Non-rejection trade → untouched.
    ok = {"channel": "trade", "data": {"state": "COMPLETED"}}
    assert "rejection" not in streaming._annotate_rejection(ok)

    # bbo carries no rejections → untouched even if the data looks odd.
    bbo = {"channel": "bbo", "data": {"state": "REJECTED"}}
    assert "rejection" not in streaming._annotate_rejection(bbo)


@pytest.mark.asyncio
async def test_poll_annotates_rejected_events(monkeypatch: pytest.MonkeyPatch) -> None:
    polled = {
        "subscription_id": "s1",
        "channel": "trade",
        "connected": True,
        "cursor": 2,
        "events": [
            {"seq": 1, "channel": "trade", "data": {"state": "COMPLETED"}},
            {"seq": 2, "channel": "trade", "data": {"state": "REJECTED", "reason": "PRICE"}},
        ],
    }

    class _FakeManager:
        async def poll(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return polled

    async def fake_manager() -> Any:
        return _FakeManager()

    monkeypatch.setattr(streaming, "get_ws_manager", fake_manager)
    out = await streaming.paradigm_poll("s1")
    assert "rejection" not in out["events"][0]
    assert out["events"][1]["rejection"]["reason"] == "PRICE"
