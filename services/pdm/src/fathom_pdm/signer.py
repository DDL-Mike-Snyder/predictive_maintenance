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
        self._key = os.environb.get(
            b"FATHOM_PLACEHOLDER_SIGNING_KEY", b"placeholder-key-not-for-production"
        )

    def sign(self, payload_sha256: bytes) -> tuple[bytes, str]:
        digest = hmac.new(self._key, payload_sha256, hashlib.sha256).digest()
        return digest, "placeholder-signing-key"

    def verify(
        self,
        payload_sha256: bytes,
        signature: bytes,
        signing_key_id: str,  # noqa: ARG002
    ) -> bool:
        # Single fixed key today (see __init__'s own [PLACEHOLDER] note), so
        # signing_key_id has nothing to select between yet -- a real,
        # Vault/HSM-backed implementation resolves the actual key by this id.
        expected, _ = self.sign(payload_sha256)
        return hmac.compare_digest(expected, signature)

    def encrypt(self, payload_json: bytes) -> tuple[bytes | None, str]:
        # [PLACEHOLDER] No real encryption -- Audit's key-custody boundary
        # (32-audit.md) owns per-classification envelope encryption.
        return payload_json, "placeholder-kek"

    def decrypt(self, payload_ciphertext: bytes, kek_id: str) -> bytes:  # noqa: ARG002 -- see encrypt()
        # [PLACEHOLDER] encrypt()'s inverse -- `payload_ciphertext` IS the
        # plaintext JSON today, so this is a passthrough, not a real decrypt.
        return payload_ciphertext
