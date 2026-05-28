# mcp-paradigm-py

MCP server for the **Paradigm DRFQv2** bilateral RFQ trading platform.
Exposes the Paradigm REST surface as typed tools to any MCP client
(Claude Code, Claude Desktop, any IDE with MCP support).

> See [`DESIGN.md`](DESIGN.md) for the full design — tool surface,
> auth model, signing layer, deployment posture.

## Install

```bash
# from PyPI
pip install mcp-paradigm

# or one-shot via uvx (no install)
uvx mcp-paradigm

# or for local development
git clone https://github.com/tradeparadigm/mcp-paradigm-py.git
cd mcp-paradigm-py
just install-dev
```

Claude Desktop users: install the prebuilt `.mcpb` bundle from the
latest [GitHub release](https://github.com/tradeparadigm/mcp-paradigm-py/releases)
— double-click to install, then enter your access key + signing key
when prompted.

## Configure

Set your Paradigm access key and signing key. The signing key is
base64-encoded as issued by Paradigm.

```bash
export PARADIGM_ACCESS_KEY="..."         # bearer token (access key id)
export PARADIGM_SIGNING_KEY="..."        # base64-encoded HMAC key
export PARADIGM_ENVIRONMENT="testnet"    # or "prod"
# Optional overrides:
# export PARADIGM_BASE_URL="https://api.test.paradigm.co"
# export PARADIGM_WS_URL="wss://ws.api.test.paradigm.trade/v2/drfq/"
# export PARADIGM_ACCOUNT="my-desk"      # if running multi-desk
```

## Run

```bash
# stdio transport — for Claude Desktop / Claude Code
mcp-paradigm

# streamable-http — for remote agents
mcp-paradigm --transport streamable-http --port 3000
```

### Wiring into Claude Code / Desktop

```json
{
  "mcpServers": {
    "paradigm": {
      "command": "mcp-paradigm",
      "env": {
        "PARADIGM_ACCESS_KEY": "...",
        "PARADIGM_SIGNING_KEY": "...",
        "PARADIGM_ENVIRONMENT": "testnet"
      }
    }
  }
}
```

## Smoke test

After wiring up the server, call `paradigm_echo` first. A 200 response
confirms your access key, signing key, and environment are all correct.
If signing is broken you'll see a 401 with `Invalid signature`.

## Tool surface

Grouped by responsibility — see DESIGN.md for the full mapping to
Paradigm REST endpoints, scopes, and approval gates.

| Group | Tools |
|---|---|
| Reference data | `paradigm_instruments`, `paradigm_instrument`, `paradigm_counterparties`, `paradigm_platform_state` |
| RFQ lifecycle | `paradigm_rfqs`, `paradigm_rfq`, `paradigm_rfq_bbo`, `paradigm_rfq_orders`, `paradigm_create_rfq`, `paradigm_cancel_rfq` |
| Order lifecycle | `paradigm_orders`, `paradigm_order`, `paradigm_post_order`, `paradigm_update_order`, `paradigm_cancel_order`, `paradigm_cancel_orders_batch` |
| Trades | `paradigm_trades`, `paradigm_trade`, `paradigm_trade_tape` |
| Pricing | `paradigm_price_legs` |
| MMP | `paradigm_mmp_status`, `paradigm_mmp_reset` |
| Self-test | `paradigm_echo` |

Tools that put money on the wire (`paradigm_post_order`,
`paradigm_update_order`, `paradigm_create_rfq`, `paradigm_mmp_reset`)
are annotated `destructiveHint=true` so MCP clients can show an
approval prompt before execution.

## Development

```bash
just check       # format + lint + test
just test        # pytest only
just mcpb        # build .mcpb bundle for Claude Desktop
just build       # sdist + wheel
just docker      # docker build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full dev loop.

Signing is verified by `tests/test_signing.py` against the canonical
Paradigm message layout (`<timestamp>\n<METHOD>\n<path-with-query>\n<body>`).

## Status

Alpha. The REST surface is complete; WebSocket subscription tools
(`paradigm_subscribe` / `paradigm_poll` / `paradigm_unsubscribe`) and
production signers (Vault Transit, AWS KMS) are tracked in DESIGN.md.

## License

MIT — see [LICENSE](LICENSE).
