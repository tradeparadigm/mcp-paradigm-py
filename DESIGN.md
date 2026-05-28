# `mcp-paradigm-py` — design

The MCP server wraps the Paradigm REST surfaces and exposes a typed
tool surface to Claude Code / Claude Desktop / any MCP-aware client.

## Product coverage

| Product | Status | REST host | Path prefix | Covered |
|---|---|---|---|---|
| **DRFQv2** — bilateral RFQ | active | `api.{prod\|testnet}.paradigm.trade` | `/v2/drfq/` | ✓ 22 tools |
| **OBv1** — Unified Markets order books | active | `api.{prod\|testnet}.paradigm.trade` | `/v1/ob/` | ✓ 23 tools |
| **FSPD** — Future Spread Direct | active | `api.fs.{prod\|testnet}.paradigm.co` | `/v1/fs/` | ✓ 19 tools |
| **Firm** — identity / positions / leaderboard | active | `api.{prod\|testnet}.paradigm.trade` | `/v1/identity/`, `/v1/positions/`, `/v1/leaderboard/` | ✓ 7 tools |
| **GRFQ** — Global RFQ | being deprecated (→ OBv1) | — | `/v1/grfq/` | skip |
| **VRFQ** — Vanilla RFQ (Ribbon-style) | niche / contact-only | — | `/v1/vrfq/` | not planned |

OBv1 and the firm-level surfaces share the same host as DRFQv2, so
they reuse `get_paradigm_client()`. FSPD lives on its own host and
uses `get_fspd_client()`.

---

## 1. Goals and non-goals

**Goals:**

1. Expose Paradigm's active product REST surfaces as MCP tools — DRFQv2,
   OBv1, and FSPD all shipped, plus firm-level identity, positions, and
   leaderboards.
2. Keep the HMAC signing key out of the agent process (pluggable
   signing layer: env-var for dev, Vault Transit / AWS KMS for prod).
3. OAuth 2.1-protected per the MCP spec (2025-03-26 revision), with
   scopes that map cleanly onto tool sensitivity.
4. Surface async-first order state semantics correctly (response is
   `PENDING`; client polls or subscribes for terminal state).
5. Expose WebSocket streams via a snapshot + tail interface so MCP
   clients can consume push data without bespoke transport.

**Non-goals:**

1. **GRFQ** is being phased out by OBv1, so it isn't on the roadmap.
2. **VRFQ** is a niche surface — not planned unless requested.
2. Not a strategy engine — it executes what the caller decides. Pricing
   logic, edge application, etc. live in the calling skill.
3. Not a credential vault — it consumes a signing capability, doesn't
   manage it. Vault Transit / KMS / the credential registry are
   separate services.
4. Not a UI — agents call it; humans use the registry page to manage
   keys.

---

## 2. Architecture

```
   Agent (Claude Code / Desktop)
        │
        │   OAuth 2.1 bearer (Dex / Paradex IdP issuer)
        ▼
   mcp-paradigm-py  (FastMCP server)
        │
        ├──►  ParadigmClient (httpx)
        │         │
        │         │ auth hook
        │         ▼
        │     Signing layer (pluggable)
        │         │  ┌──────────────────────────┐
        │         ├──┤ EnvKeySigner            │  dev / local (shipped)
        │         ├──┤ VaultTransitSigner      │  prod (planned)
        │         ├──┤ KMSGenerateMacSigner    │  prod (planned)
        │         └──┤ SidecarHttpSigner       │  custom (planned)
        │            └──────────────────────────┘
        │
        └──►  Paradigm REST (api.paradigm.co or api.test.paradigm.co)
```

---

## 3. Tool surface

Conventions:

- `paradigm_*` prefix.
- Snake_case.
- Singular = "get one"; plural = "list".
- All list tools accept `cursor` and `page_size` for pagination.

### 3.1 Reference data

| Tool | REST | Purpose |
|---|---|---|
| `paradigm_instruments` | `GET /v2/drfq/instruments/` | List tradable instruments |
| `paradigm_instrument` | `GET /v2/drfq/instruments/{id}/` | Fetch one instrument by id |
| `paradigm_counterparties` | `GET /v2/drfq/counterparties/` | List desks the firm can RFQ |
| `paradigm_platform_state` | `GET /v2/drfq/platform_state/` | Maintenance windows |

### 3.2 RFQ lifecycle (taker)

| Tool | REST | Scope | Approval |
|---|---|---|---|
| `paradigm_rfqs` | `GET /v2/drfq/rfqs/` | `paradigm:read` | no |
| `paradigm_rfq` | `GET /v2/drfq/rfqs/{id}/` | `paradigm:read` | no |
| `paradigm_rfq_bbo` | `GET /v2/drfq/rfqs/{id}/bbo/` | `paradigm:read` | no |
| `paradigm_rfq_orders` | `GET /v2/drfq/rfqs/{id}/orders/` | `paradigm:read` | no |
| `paradigm_create_rfq` | `POST /v2/drfq/rfqs/` | `paradigm:create_rfq` | **yes** |
| `paradigm_cancel_rfq` | `DELETE /v2/drfq/rfqs/{id}/` | `paradigm:cancel` | no |

### 3.3 Order lifecycle (maker quote + taker cross)

| Tool | REST | Scope | Approval |
|---|---|---|---|
| `paradigm_orders` | `GET /v2/drfq/orders/` | `paradigm:read` | no |
| `paradigm_order` | `GET /v2/drfq/orders/{id}/` | `paradigm:read` | no |
| `paradigm_post_order` | `POST /v2/drfq/orders/` | `paradigm:post_order` | **yes** |
| `paradigm_update_order` | `PUT /v2/drfq/orders/{id}/` | `paradigm:post_order` | **yes** |
| `paradigm_cancel_order` | `DELETE /v2/drfq/orders/{id}/` | `paradigm:cancel` | no |
| `paradigm_cancel_orders_batch` | `DELETE /v2/drfq/orders/` | `paradigm:cancel` | no |

### 3.4 Trades

| Tool | REST |
|---|---|
| `paradigm_trades` | `GET /v2/drfq/trades/` |
| `paradigm_trade` | `GET /v2/drfq/trades/{id}/` |
| `paradigm_trade_tape` | `GET /v2/drfq/trade_tape/` |

### 3.5 Pricing and MMP

| Tool | REST | Approval |
|---|---|---|
| `paradigm_price_legs` | `POST /v2/drfq/pricing/` | no |
| `paradigm_mmp_status` | `GET /v2/drfq/mmp/status/` | no |
| `paradigm_mmp_reset` | `PATCH /v2/drfq/mmp/status/` | **yes** |

### 3.6 Self-test

| Tool | REST |
|---|---|
| `paradigm_echo` | `GET` / `POST /v2/drfq/echo/` |

### 3.7 WebSocket subscriptions (planned)

WS events don't map naturally to request/response tools. The server
will hold one WS connection per session and expose:

| Tool | Behavior |
|---|---|
| `paradigm_subscribe(channel)` | Open a subscription, return `subscription_id`. Channels: `rfq`, `order`, `trade`, `trade_confirmation`, `bbo`, `mmp` |
| `paradigm_poll(subscription_id, since?, limit?)` | Drain buffered events; returns `events[]` and next cursor |
| `paradigm_unsubscribe(subscription_id)` | Close a subscription |

---

## 4. Auth model

### 4.1 Inbound (MCP client → server)

OAuth 2.1 resource server per the MCP spec 2025-03-26 revision (planned
for the HTTP transport).

- Server publishes
  `WWW-Authenticate: Bearer resource_metadata=…/.well-known/oauth-protected-resource`
  on 401.
- Resource metadata points at the trusted authorization server.
- Server validates incoming JWTs against the AS's JWKS.

### 4.2 Outbound (server → Paradigm)

Bearer access key + HMAC signature triple. Computed by the Signer at
the moment of each request — when running with Vault / KMS the
signing key never lives in the agent process.

Canonical signing message:

```
<timestamp_ms>\n<METHOD>\n<path-with-query>\n<body>
```

HMAC-SHA256 over the base64-decoded signing key, then base64-encoded.
Sent as `Paradigm-API-Signature` with `Paradigm-API-Timestamp`.

### 4.3 Scopes (planned)

| Scope | Tools |
|---|---|
| `paradigm:read` | All GETs + pricing |
| `paradigm:create_rfq` | `paradigm_create_rfq` |
| `paradigm:post_order` | `paradigm_post_order`, `paradigm_update_order` |
| `paradigm:cancel` | `paradigm_cancel_rfq`, `paradigm_cancel_order`, `paradigm_cancel_orders_batch` |
| `paradigm:mmp` | `paradigm_mmp_reset` |
| `paradigm:subscribe` | `paradigm_subscribe`, `paradigm_poll`, `paradigm_unsubscribe` |

---

## 5. Signing layer interface

```python
from typing import Protocol

class Signer(Protocol):
    def sign(self, method: str, path: str, body_bytes: bytes) -> tuple[str, str]:
        """Return (timestamp_ms_str, base64_signature)."""
```

### 5.1 Reference implementations

- **`EnvKeySigner`** (shipped) — reads `PARADIGM_SIGNING_KEY`, computes
  HMAC in-process. Dev / local only.
- **`VaultTransitSigner`** (planned) — delegates to Vault Transit's
  `hmac/{key_name}/sha256`.
- **`KMSGenerateMacSigner`** (planned) — AWS KMS `kms:GenerateMac`.
- **`SidecarHttpSigner`** (planned) — POSTs the canonical message to a
  local signing service.

### 5.2 Selection

```bash
PARADIGM_SIGNING_DRIVER=env_key   # env_key | vault_transit | aws_kms | sidecar
```

---

## 6. Repo layout

```
mcp-paradigm-py/
├── pyproject.toml
├── README.md
├── DESIGN.md
├── src/mcp_paradigm/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server/server.py            # FastMCP entrypoint, run_cli
│   ├── tools/
│   │   ├── reference_data.py       # instruments, counterparties, platform_state
│   │   ├── rfqs.py                 # rfq lifecycle
│   │   ├── orders.py               # order lifecycle
│   │   ├── trades.py               # trades + tape
│   │   ├── pricing.py
│   │   ├── mmp.py
│   │   └── echo.py
│   └── utils/
│       ├── config.py               # env-driven config
│       ├── errors.py               # typed exceptions
│       ├── signing.py              # Signer protocol + EnvKeySigner
│       └── paradigm_client.py      # async REST client w/ signing
├── tests/
│   ├── test_signing.py             # canonical-message vectors
│   └── test_client.py              # httpx MockTransport assertions
└── docker/Dockerfile
```

---

## 7. Configuration

| Env var | Default | Purpose |
|---|---|---|
| `PARADIGM_ACCESS_KEY` | — | Bearer access key |
| `PARADIGM_SIGNING_KEY` | — | Base64 HMAC key |
| `PARADIGM_ENVIRONMENT` | `prod` | `prod` or `testnet` |
| `PARADIGM_BASE_URL` | derived | Override REST base URL |
| `PARADIGM_WS_URL` | derived | Override WS URL |
| `PARADIGM_ACCOUNT` | — | Optional multi-desk header |
| `PARADIGM_SIGNING_DRIVER` | `env_key` | Selects Signer implementation |
| `PARADIGM_TIMEOUT` | `30` | HTTP timeout (seconds) |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `MCP_PORT` | `3000` | HTTP transport port |

---

## 8. Testing

Three layers:

1. **Signing unit tests** (`tests/test_signing.py`) — canonical message
   layout and key reuse, independently re-implemented for the assertion.
2. **Client tests** (`tests/test_client.py`) — `httpx.MockTransport`
   asserts the headers, path-with-query, and body bytes the server
   would send.
3. **Integration tests** (planned) — point at `api.test.paradigm.co`,
   hit `paradigm_echo`, then RFQ create + cancel against a known-safe
   synthetic instrument. Tagged `@pytest.mark.integration`; skipped by
   default.

---

## 9. Open questions

1. **Per-session vs per-process WS connection.** Per-session needs the
   server to map OAuth `sub` to a WS identity; per-process is simpler
   but conflates fills across users.
2. **Should `paradigm_post_order` block until terminal state?** Default
   to return-immediately + tool annotation that the caller should poll
   or subscribe. Optional `wait_for_terminal: bool = false` later.
3. **Step-up auth for `paradigm:post_order`** — per-call is safer for
   live money but breaks maker streaming. Per-session by default.
4. **Idempotency** — Paradigm's `label` is documented but no explicit
   retry guarantee. Server **never** retries POSTs; failures surface
   to the caller.
5. **Cancel-on-disconnect default** for WS — `true` is safer for
   makers, `false` for read-only agents. Make it explicit at
   subscribe time.
