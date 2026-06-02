"""Guard the distribution metadata against drifting from the code.

`manifest.json` (the Claude Desktop MCPB bundle) and the version strings
across the four release files are hand-maintained; these tests fail if the
manifest's advertised tools diverge from the registry, or if a version bump
misses one of the files. Both have already happened (the manifest lagged the
3 streaming tools; the docs once claimed the wrong tool count).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from mcp_paradigm import __version__
from mcp_paradigm.server.server import server

_ROOT = Path(__file__).resolve().parent.parent


def _load_json(name: str) -> dict:
    return json.loads((_ROOT / name).read_text())


@pytest.mark.asyncio
async def test_manifest_tools_match_registered_tools() -> None:
    manifest = _load_json("manifest.json")
    manifest_tools = {t["name"] for t in manifest["tools"]}
    registered = {t.name for t in await server.list_tools()}
    assert manifest_tools == registered, (
        "manifest.json tool list is out of sync with the registered tools. "
        f"missing from manifest: {sorted(registered - manifest_tools)}; "
        f"stale in manifest: {sorted(manifest_tools - registered)}"
    )


def test_version_is_consistent_across_release_files() -> None:
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    server_json = _load_json("server.json")
    versions = {
        "__init__.py": __version__,
        "pyproject.toml": pyproject["project"]["version"],
        "manifest.json": _load_json("manifest.json")["version"],
        "server.json (top)": server_json["version"],
        "server.json (package)": server_json["packages"][0]["version"],
    }
    unique = set(versions.values())
    assert len(unique) == 1, f"version drift across release files: {versions}"
