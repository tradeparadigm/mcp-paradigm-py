"""Tool modules registered with the FastMCP server.

Importing each submodule runs its decorators and attaches the tools to
the server singleton in ``mcp_paradigm.server.server``.

Consolidation principles:
- One list-with-id-filter tool per resource type (not separate list/get)
- One action-flag tool for status/reset pairs (MMP)
- Workflow tools (``paradigm_desk_overview``, ``paradigm_kill_switch``,
  ``paradigm_drfqv2_rfq_snapshot``, ``paradigm_obv1_market_snapshot``)
  compose multiple REST calls
"""

from . import (
    echo,
    firm,
    fspd,
    mmp,
    obv1,
    orders,
    pricing,
    reference_data,
    rfqs,
    trades,
    workflow,
)
