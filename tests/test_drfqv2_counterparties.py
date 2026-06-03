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
async def test_counterparties_no_venue_returns_pagination_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = {"results": [{"desk_name": "A"}], "next": "c1", "count": 7}
    client = _FakeClient({None: page})

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties()
    # Unfiltered: a single normalized page with an explicit cursor contract.
    assert out["count"] == 1
    assert out["next_cursor"] == "c1"
    assert out["has_more"] is True
    assert out["total"] == 7  # DRF grand total surfaced
    assert out["results"][0]["desk_name"] == "A"
    # Prime is annotated as None when the payload carries no prime signal.
    assert out["results"][0]["prime_venue_enabled"] is None
    assert len(client.calls) == 1  # one page, not a full walk


@pytest.mark.asyncio
async def test_counterparties_no_next_cursor_has_more_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # DRF full-URL `next` is not a reusable cursor → has_more is False.
    page = {"results": [{"desk_name": "A"}], "next": "https://api/x?cursor=z"}
    client = _FakeClient({None: page})

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties()
    assert out["next_cursor"] is None
    assert out["has_more"] is False


@pytest.mark.asyncio
async def test_counterparties_fetch_all_walks_every_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = {
        None: {"results": [{"desk_name": "A"}], "next": "c1"},
        "c1": {"results": [{"desk_name": "B"}], "next": None},
    }
    client = _FakeClient(pages)

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties(fetch_all=True)
    assert out["count"] == 2
    assert out["scanned"] == 2
    assert out["truncated"] is False
    assert {d["desk_name"] for d in out["results"]} == {"A", "B"}
    assert len(client.calls) == 2


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


def test_desk_prime_venue_enabled_across_shapes() -> None:
    # Explicit prime-venue list, membership-checked against the venue.
    prime_list = {"desk_name": "A", "prime_venues": ["PRDX", {"code": "DBT"}]}
    assert reference._desk_prime_venue_enabled(prime_list, "PRDX") is True
    assert reference._desk_prime_venue_enabled(prime_list, "BIT") is False
    assert reference._desk_prime_venue_enabled(prime_list) is True  # any prime venue

    # Top-level boolean.
    assert reference._desk_prime_venue_enabled({"is_prime": True}) is True
    assert reference._desk_prime_venue_enabled({"prime": False}) is False

    # Prime marker inside groups.
    assert reference._desk_prime_venue_enabled({"groups": ["PRIME_LP"]}) is True
    assert reference._desk_prime_venue_enabled({"groups": [{"name": "retail"}]}) is False

    # No prime signal anywhere → None (distinct from False).
    assert reference._desk_prime_venue_enabled({"desk_name": "A", "venues": ["PRDX"]}) is None
    assert reference._desk_prime_venue_enabled("nope") is None


@pytest.mark.asyncio
async def test_counterparties_prime_only_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        None: {
            "results": [
                {"desk_name": "A", "venues": ["PRDX"], "prime_venues": ["PRDX"]},
                {"desk_name": "B", "venues": ["PRDX"], "prime_venues": ["DBT"]},
            ],
            "next": None,
        },
    }
    client = _FakeClient(pages)

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties(venue="PRDX", prime_only=True)
    assert out["venue"] == "PRDX"
    assert {d["desk_name"] for d in out["results"]} == {"A"}
    assert out["results"][0]["prime_venue_enabled"] is True
    assert "note" not in out


@pytest.mark.asyncio
async def test_counterparties_prime_only_notes_when_no_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No desk carries any prime signal → empty result + explanatory note.
    pages = {None: {"results": [{"desk_name": "A", "venues": ["PRDX"]}], "next": None}}
    client = _FakeClient(pages)

    async def fake_client() -> Any:
        return client

    monkeypatch.setattr(reference, "get_paradigm_client", fake_client)
    out = await reference.paradigm_drfqv2_counterparties(prime_only=True)
    assert out["results"] == []
    assert "note" in out


def test_create_rfq_counterparties_defaults_to_broadcast() -> None:
    """Empty counterparties is the default broadcast-to-all-eligible path."""
    import inspect

    sig = inspect.signature(rfqs.paradigm_drfqv2_create_rfq)
    default = sig.parameters["counterparties"].default
    assert default == []
