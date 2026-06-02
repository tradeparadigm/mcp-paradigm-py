"""DRFQv2 (bilateral RFQ) tool modules.

Importing each submodule runs its decorators and attaches the tools to
the server singleton in ``mcp_paradigm.server.server``.
"""

from . import (
    mmp,
    orders,
    pricing,
    reference,
    rfqs,
    streaming,
    trades,
)
