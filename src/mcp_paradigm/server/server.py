"""FastMCP server entry point for Paradigm DRFQv2."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp.server import FastMCP

from mcp_paradigm import __version__
from mcp_paradigm.utils.config import config

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("mcp-paradigm")


def create_server() -> FastMCP:
    """Build the FastMCP server instance with description and metadata."""
    return FastMCP(
        name=config.SERVER_NAME,
        instructions=f"""Paradigm DRFQv2 MCP Server v{__version__}.

Wraps the Paradigm bilateral RFQ REST surface. Outbound requests are
HMAC-signed by the configured Signer (env-key for dev; Vault Transit
or AWS KMS in prod). Tools are grouped by responsibility:

• Reference  — paradigm_instruments, paradigm_instrument,
               paradigm_counterparties, paradigm_platform_state
• RFQs       — paradigm_rfqs, paradigm_rfq, paradigm_rfq_bbo,
               paradigm_rfq_orders, paradigm_create_rfq (gated),
               paradigm_cancel_rfq
• Orders     — paradigm_orders, paradigm_order, paradigm_post_order
               (gated), paradigm_update_order (gated),
               paradigm_cancel_order, paradigm_cancel_orders_batch
• Trades     — paradigm_trades, paradigm_trade, paradigm_trade_tape
• Pricing    — paradigm_price_legs
• MMP        — paradigm_mmp_status, paradigm_mmp_reset (gated)
• Self-test  — paradigm_echo (round-trip to verify signing + auth)

Start with paradigm_echo to confirm signing is wired up. Then
paradigm_platform_state for operational status.""",
    )


server = create_server()


# Register tools. Imports run their module-level decorators which attach
# tools to the singleton `server`. F401-safe; see tools/__init__.py.
import mcp_paradigm.tools  # noqa: E402, F401


def run_cli() -> None:
    """CLI entry point declared in pyproject.toml."""
    parser = argparse.ArgumentParser(description="MCP Paradigm Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport (default: stdio) [env: MCP_TRANSPORT]",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", str(config.SERVER_PORT))),
        help=f"Port for streamable-http (default: {config.SERVER_PORT}) [env: MCP_PORT]",
    )
    args = parser.parse_args()

    if not config.is_configured():
        logger.warning(
            "PARADIGM_ACCESS_KEY and PARADIGM_SIGNING_KEY are not both set; "
            "tools that call the Paradigm API will fail until they are."
        )

    logger.info("Starting MCP Paradigm server (transport=%s)", args.transport)
    try:
        if args.transport == "streamable-http":
            server.settings.port = args.port
            server.settings.host = "0.0.0.0"
            server.run(transport="streamable-http")
        else:
            server.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as exc:  # pragma: no cover
        logger.exception("Server crashed: %s", exc)
        sys.exit(1)


__all__ = ["server", "run_cli", "create_server"]
