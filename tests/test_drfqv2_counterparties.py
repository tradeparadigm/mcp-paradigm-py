"""Tests for the DRFQv2 counterparties venue filter + create_rfq broadcast default."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_paradigm.tools.drfqv2 import reference, rfqs


def test_desk_supports_venue_handles_both_shapes() -> None:
    bare = {"desk_name": "A", "venues": ["PRDX", "DBT"]}
    objs = {"desk_name": "B", "venues": [{"name": "prdx"}, {"code": "BIT"}]}
    assert reference._desk_supports_venue(bare, "PRDX")
    assert reference._desk_supports_venue(bare, "prdx")  # case-insensitive
    assert reference._desk_supports_venue(objs, "PRDX")  # object + lowercase
    assert reference._desk_supports_venue(objs, "BIT")
    assert not reference._desk_supports_venue(bare, "BIT")
    assert not reference._desk_supports_venue({"venues": None}, "PRDX")
    assert not reference._desk_supports_venue("nope", "PRDX")


def test_list_items_and_next_cursor() -> None:
    assert reference._list_items([1, 2]) == [1, 2]
    assert reference._list_items({"results": [1]}) == [1]
    assert reference._list_items({"data": [2]}) == [2]
    assert reference._list_items({"nope": 1}) == []

    assert reference._next_cursor({"next": "c1"}) == "c1"
    assert reference._next_cursor({"next_cursor": "c2"}) == "c2"
    # full URLs are not reusable cursor tokens
    assert reference._next_cursor({"next": "https://api/next?cursor=x"}) is None
    assert reference._next_cursor([]) is None


class _FakeClient:
    """Returns canned counterparty pages keyed by the cursor passed in."""

    def __init__(self, pages: dict[Any, dict[str, Any]]) -> None:
        self.pages = pages
        self.calls: list[dict[str, Any]] = []

    async def get(self, _path: str, **params: Any) -> Any:
        self.calls.append(params)
        return self.pages[params.get("cursor")]


@pytest.mark.asyncio
async def test_counterparties_no_venue_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    page = {"results": [{"desk_name": "A"}], "next": "c1"}
    client = _FakeClient({None: page})

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties()
    # Unfiltered: the raw single-page envelope is returned untouched.
    assert out == page
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_counterparties_venue_filter_pages_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = {
        None: {
            "results": [
                {"desk_name": "A", "venues": ["PRDX", "DBT"]},
                {"desk_name": "B", "venues": ["DBT"]},
            ],
            "next": "c1",
        },
        "c1": {
            "results": [{"desk_name": "C", "venues": [{"name": "PRDX"}]}],
            "next": None,
        },
    }
    client = _FakeClient(pages)

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties(venue="PRDX")

    assert out["venue"] == "PRDX"
    assert out["scanned"] == 3
    assert out["count"] == 2
    assert out["truncated"] is False  # reached the last page → complete
    assert {d["desk_name"] for d in out["results"]} == {"A", "C"}
    # Walked both pages.
    assert len(client.calls) == 2


def test_create_rfq_counterparties_defaults_to_broadcast() -> None:
    """Empty counterparties is the default broadcast-to-all-eligible path."""
    import inspect

    sig = inspect.signature(rfqs.paradigm_drfqv2_create_rfq)
    default = sig.parameters["counterparties"].default
    assert default == []
