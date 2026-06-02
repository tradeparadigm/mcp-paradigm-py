"""Tests that write tools surface structured rejections.

A rejected RFQ/order/trade comes back as an ordinary 2xx with a coarse
state, so the typed-exception path never fires. These tools attach a
``rejection`` block (reason/code/message/request_id/timestamp) so the
agent learns *why* in one shot instead of seeing a bare ``REJECTED``.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcp_paradigm.tools.drfqv2 import orders, rfqs, trades


class _FakeClient:
    def __init__(self, body: Any) -> None:
        self._body = body
        self._meta = {"request_id": "req-7", "timestamp": "2026-06-02T00:00:00Z"}

    async def post(self, _path: str, *, with_meta: bool = False, **_kwargs: Any) -> Any:
        return (self._body, self._meta) if with_meta else self._body

    async def put(self, _path: str, *, with_meta: bool = False, **_kwargs: Any) -> Any:
        return (self._body, self._meta) if with_meta else self._body

    async def get(self, _path: str, **_params: Any) -> Any:
        return self._body


def _patch(monkeypatch: pytest.MonkeyPatch, module: Any, body: Any) -> None:
    async def fake_client() -> Any:
        return _FakeClient(body)

    monkeypatch.setattr(module, "get_paradigm_client", fake_client)


@pytest.mark.asyncio
async def test_create_rfq_attaches_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, rfqs, {"id": "r1", "state": "REJECTED", "error": "no_makers"})
    out = await rfqs.paradigm_drfqv2_create_rfq(
        venue="PRDX", legs=[rfqs.LegCreate(instrument_id=1, ratio="1", side="BUY")], quantity="1"
    )
    assert out["rejection"]["reason"] == "no_makers"
    assert out["rejection"]["request_id"] == "req-7"
    assert out["rejection"]["timestamp"] == "2026-06-02T00:00:00Z"


@pytest.mark.asyncio
async def test_create_rfq_passes_through_when_not_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, rfqs, {"id": "r1", "state": "OPEN"})
    out = await rfqs.paradigm_drfqv2_create_rfq(
        venue="PRDX", legs=[rfqs.LegCreate(instrument_id=1, ratio="1", side="BUY")], quantity="1"
    )
    assert "rejection" not in out
    assert out["state"] == "OPEN"


@pytest.mark.asyncio
async def test_post_order_attaches_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, orders, {"id": "o1", "state": "REJECTED", "rejection_reason": "MMP_FIRED"})
    out = await orders.paradigm_drfqv2_post_order(
        rfq_id="r1", side="BUY", quantity="1", price="100"
    )
    assert out["rejection"]["reason"] == "MMP_FIRED"
    assert out["rejection"]["request_id"] == "req-7"


@pytest.mark.asyncio
async def test_trades_list_enriches_rejected_records(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "results": [
            {"id": "t1", "state": "COMPLETED"},
            {"id": "t2", "state": "REJECTED", "reason": "PRICE_OUT_OF_BAND"},
        ]
    }
    _patch(monkeypatch, trades, body)
    out = await trades.paradigm_drfqv2_trades()
    assert "rejection" not in out["results"][0]
    assert out["results"][1]["rejection"]["reason"] == "PRICE_OUT_OF_BAND"
