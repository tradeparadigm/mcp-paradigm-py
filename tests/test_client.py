"""HTTP client tests — assert the signing path used by httpx and the headers."""

from __future__ import annotations

import base64

import httpx
import pytest

from mcp_paradigm.utils.paradigm_client import ParadigmClient, _path_with_query
from mcp_paradigm.utils.signing import EnvKeySigner


def test_path_with_query_serialization() -> None:
    assert _path_with_query("/v2/x/", None) == "/v2/x/"
    assert _path_with_query("/v2/x/", {"a": None}) == "/v2/x/"
    assert _path_with_query("/v2/x/", {"a": 1, "b": "z"}) == "/v2/x/?a=1&b=z"
    assert _path_with_query("/v2/x/", {"a": True}) == "/v2/x/?a=true"
    out = _path_with_query("/v2/x/", {"names": ["a", "b"]})
    assert out == "/v2/x/?names=a&names=b"


@pytest.mark.asyncio
async def test_client_signs_get(monkeypatch: pytest.MonkeyPatch) -> None:
    key_b64 = base64.b64encode(b"k" * 32).decode("ascii")
    signer = EnvKeySigner(signing_key_b64=key_b64)

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = ParadigmClient(
        base_url="https://api.test.paradigm.co",
        access_key="ak_test",
        signer=signer,
    )
    client._client = httpx.AsyncClient(
        base_url="https://api.test.paradigm.co", transport=transport
    )

    result = await client.get("/v2/drfq/echo/")
    await client.close()

    assert result == {"ok": True}
    assert captured["method"] == "GET"
    headers = captured["headers"]  # type: ignore[assignment]
    assert headers["authorization"] == "Bearer ak_test"
    assert "paradigm-api-timestamp" in headers
    assert "paradigm-api-signature" in headers


@pytest.mark.asyncio
async def test_client_signs_post_body(monkeypatch: pytest.MonkeyPatch) -> None:
    key_b64 = base64.b64encode(b"k" * 32).decode("ascii")
    signer = EnvKeySigner(signing_key_b64=key_b64)

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = bytes(request.content)
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json={"echo": True})

    transport = httpx.MockTransport(handler)
    client = ParadigmClient(
        base_url="https://api.test.paradigm.co",
        access_key="ak_test",
        signer=signer,
    )
    client._client = httpx.AsyncClient(
        base_url="https://api.test.paradigm.co", transport=transport
    )

    await client.post("/v2/drfq/echo/", json_body={"hello": "world"})
    await client.close()

    assert captured["content"] == b'{"hello":"world"}'
    assert captured["content_type"] == "application/json"
