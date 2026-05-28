"""Pluggable signing layer for Paradigm HMAC auth.

The signing key never has to live in the agent process. Implementations
of ``Signer`` may compute HMAC locally (``EnvKeySigner``) or delegate to
Vault Transit, AWS KMS, or a sidecar HTTP signer. See ``DESIGN.md``.

Paradigm's signing message is the literal string::

    <timestamp_ms>\\n<METHOD>\\n<path-with-query>\\n<body>

signed with HMAC-SHA256 over the base64-decoded signing key, then
base64-encoded.
"""

from __future__ import annotations

import base64
import hmac
import time
from hashlib import sha256
from typing import Protocol

from mcp_paradigm.utils.config import config


class Signer(Protocol):
    """Sign a Paradigm REST request.

    Returns ``(timestamp_ms_str, base64_signature)``. The timestamp must
    be within 30s of Paradigm server time.
    """

    def sign(self, method: str, path: str, body_bytes: bytes) -> tuple[str, str]: ...


def build_message(timestamp_ms: str, method: str, path: str, body_bytes: bytes) -> bytes:
    """Construct the canonical message Paradigm signs over."""
    return b"\n".join(
        [
            timestamp_ms.encode("ascii"),
            method.upper().encode("ascii"),
            path.encode("utf-8"),
            body_bytes,
        ]
    )


class EnvKeySigner:
    """Reads the signing key from env, computes HMAC in-process. Dev only."""

    def __init__(self, signing_key_b64: str | None = None) -> None:
        key = signing_key_b64 or config.PARADIGM_SIGNING_KEY
        if not key:
            raise ValueError(
                "PARADIGM_SIGNING_KEY is not set; cannot use EnvKeySigner."
            )
        self._key = base64.b64decode(key)

    def sign(self, method: str, path: str, body_bytes: bytes) -> tuple[str, str]:
        ts = str(int(time.time() * 1000))
        msg = build_message(ts, method, path, body_bytes)
        digest = hmac.new(self._key, msg, sha256).digest()
        return ts, base64.b64encode(digest).decode("ascii")


def get_signer() -> Signer:
    """Resolve the configured Signer implementation.

    Only ``env_key`` is currently shipped. Vault Transit / AWS KMS /
    Sidecar implementations are listed in ``DESIGN.md`` and will be
    added when the corresponding production backend is wired up.
    """
    driver = config.SIGNING_DRIVER.lower()
    if driver == "env_key":
        return EnvKeySigner()
    raise NotImplementedError(
        f"Signing driver {driver!r} is not implemented; only 'env_key' is shipped."
    )
