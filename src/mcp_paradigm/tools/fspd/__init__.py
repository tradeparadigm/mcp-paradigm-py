"""FSPD (Future Spread Direct) tool modules.

Importing each submodule runs its decorators and attaches the tools to
the server singleton in ``mcp_paradigm.server.server``.
"""

from . import (
    mmp,
    orderbook,
    orders,
    reference,
    system,
    trades,
)
