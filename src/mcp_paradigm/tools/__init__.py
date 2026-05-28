"""Tool modules registered with the FastMCP server.

Importing each submodule runs its decorators and attaches the tools to
the server singleton in ``mcp_paradigm.server.server``.
"""

from . import (  # noqa: F401
    echo,
    mmp,
    orders,
    pricing,
    reference_data,
    rfqs,
    trades,
)
