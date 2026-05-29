"""Guard the enum values exposed in tool input schemas.

These tests would have caught the DRFQv2 regression where ``state``/``role``
parameters advertised Python enum reprs (``"RFQState.OPEN"``,
``"AuctionRole.MAKER"``, ``"OrderState.OPEN"``) instead of the bare API
values the Paradigm API actually expects. The bad values were passed
straight through to the API as query params / request body.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from mcp_paradigm.server.server import server

# Matches a Python enum repr like "RFQState.OPEN" / "AuctionRole.MAKER".
_ENUM_REPR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def _collect_enum_values(schema: Any) -> list[str]:
    """Recursively collect every string listed under an ``enum`` in a schema."""
    found: list[str] = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "enum" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(_collect_enum_values(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_collect_enum_values(item))
    return found


@pytest.mark.asyncio
async def test_no_tool_enum_values_are_python_reprs() -> None:
    """No tool may advertise an enum value shaped like ``EnumClass.VALUE``.

    Bare API values ("OPEN", "MAKER", ...) never contain a dot, so any
    ``Word.WORD`` value means a Python enum repr leaked into the schema.
    """
    tools = await server.list_tools()
    assert tools, "expected the server to register tools"

    offenders: dict[str, list[str]] = {}
    for tool in tools:
        bad = [v for v in _collect_enum_values(tool.inputSchema) if _ENUM_REPR.match(v)]
        if bad:
            offenders[tool.name] = bad

    assert not offenders, f"tools expose Python enum reprs instead of API values: {offenders}"


@pytest.mark.asyncio
async def test_drfqv2_state_and_role_enum_values() -> None:
    """Pin the exact bare API values for the DRFQv2 state/role filters."""
    tools = {t.name: t for t in await server.list_tools()}

    def enums(tool_name: str, param: str) -> set[str]:
        prop = tools[tool_name].inputSchema["properties"][param]
        return set(_collect_enum_values(prop))

    assert enums("paradigm_drfqv2_rfqs", "state") == {"OPEN", "CLOSED", "DRAFT"}
    assert enums("paradigm_drfqv2_rfqs", "role") == {"MAKER", "TAKER"}
    assert enums("paradigm_drfqv2_create_rfq", "state") == {"OPEN", "DRAFT"}
    assert enums("paradigm_drfqv2_orders", "state") == {"OPEN", "CLOSED", "PENDING"}
