"""OBv1 (Order Books, Unified Markets) tool modules.

Importing each submodule runs its decorators and attaches the tools to
the server singleton in ``mcp_paradigm.server.server``.
"""

from . import (
    markets,
    mmp,
    orders,
    pricing,
    quotes,
    reference,
    trades,
)
