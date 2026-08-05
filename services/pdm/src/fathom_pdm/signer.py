"""[PLACEHOLDER] `SigningPort` implementation. Real envelope
signing/encryption key custody belongs to `audit`'s Vault/HSM integration
(32-audit.md §5) -- PdM, like every domain service, calls out to that
custody boundary rather than holding key material itself. This stand-in
lets the outbox/API layers be built and tested now; replace before this
service is deployed.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from fathom_sync.outbox import SigningPort


class EnvelopeSigner(SigningPort):
    def __init__(self) -> None:
        # [PLACEHOLDER] Not Vault/HSM-backed. A key from the environment,
        # standing in for the real per-classification KEK Audit manages.
        self._key = os.environb.get(b"FATHOM_PLACEHOLDER_SIGNING_KEY", b"placeholder-key-not-for-production")

    def sign(self, payload_sha256: bytes) -> tuple[bytes, str]:
        return hmac.new(self._key, payload_sha256, hashlib.sha256).digest(), "placeholder-signing-key"

    def encrypt(self, payload_json: bytes) -> tuple[bytes | None, str]:
        # [PLACEHOLDER] No real encryption -- Audit's key-custody boundary
        # (32-audit.md) owns per-classification envelope encryption.
        return payload_json, "placeholder-kek"
