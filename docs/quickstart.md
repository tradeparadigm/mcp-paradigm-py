# Quickstart

Get the Paradigm MCP server running against testnet in under two minutes.

## 1. Install

```bash
pip install mcp-paradigm
# or, for local development:
git clone https://github.com/tradeparadigm/mcp-paradigm-py.git
cd mcp-paradigm-py
just install-dev
```

## 2. Get credentials

Mint an access key + signing key from the Paradigm admin UI. You need:

- **Access key** — sent as `Authorization: Bearer <access_key>`.
- **Signing key** — base64-encoded HMAC-SHA256 key. Used to sign every
  outbound request. **Keep this secret.**

For first-time wiring use the testnet environment
(`api.test.paradigm.co`).

## 3. Configure

```bash
export PARADIGM_ACCESS_KEY="..."
export PARADIGM_SIGNING_KEY="..."   # base64 string
export PARADIGM_ENVIRONMENT="testnet"
```

Or copy `.env.template` to `.env` and fill in the same values —
`python-dotenv` will load them at import.

## 4. Smoke test

```bash
mcp-paradigm   # boots on stdio
```

In another shell, use any MCP client (or the `mcp` CLI) to call
`paradigm_echo` first. A 200 response means signing is correct.

## 5. Wire into Claude Desktop / Claude Code

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

Or install the MCPB bundle (`mcp-paradigm-0.1.0.mcpb`) from the latest
[GitHub release](https://github.com/tradeparadigm/mcp-paradigm-py/releases)
— Claude Desktop will prompt you for the access key + signing key on
first run.

## 6. First workflow

A typical taker flow:

```
paradigm_platform_state           # check exchange operational
paradigm_counterparties           # who can I RFQ?
paradigm_instruments venue=DBT    # find what's tradable
paradigm_create_rfq …             # ⚠ approval prompt
paradigm_rfq_bbo / paradigm_rfq_orders   # see quotes come in
paradigm_post_order time_in_force=FILL_OR_KILL …   # ⚠ approval prompt
paradigm_trade trade_id=…         # confirm settlement
```

`paradigm_create_rfq`, `paradigm_post_order`, `paradigm_update_order`,
and `paradigm_mmp_reset` are annotated `destructiveHint=true` — MCP
clients should display an approval prompt before invoking them.
