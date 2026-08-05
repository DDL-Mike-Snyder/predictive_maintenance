"""Test doubles for `packages/py-sync`'s ports. NOT for production use --
real signing/encryption is Audit's key-custody domain (32-audit.md); a real
`EpochFence` reads the service's own configuration read model.
"""

from __future__ import annotations

import hashlib
import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from .outbox import SigningPort


class InsecureTestSigner(SigningPort):
    """HMAC over a fixed test key. NEVER use outside a test suite."""

    def __init__(self, key: bytes = b"test-only-key") -> None:
        self._key = key

    def sign(self, payload_sha256: bytes) -> tuple[bytes, str]:
        return hmac.new(self._key, payload_sha256, hashlib.sha256).digest(), "test-signing-key"

    def encrypt(self, payload_json: bytes) -> tuple[bytes | None, str]:
        # No real encryption in the test double -- ciphertext == plaintext,
        # clearly marked so nobody mistakes this for a security boundary.
        return payload_json, "test-kek"


class FixedEpochFence:
    """An `EpochFence` that always reports a fixed current epoch, for unit
    tests that don't need real antecedent-rule blocking behavior."""

    def __init__(self, epoch: int = 0) -> None:
        self._epoch = epoch

    async def current_epoch(self, session: AsyncSession, asset_id: str) -> int:
        return self._epoch
