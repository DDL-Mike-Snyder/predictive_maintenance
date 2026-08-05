"""The OIDC/PKCE client. Document 30-gateway.md §8.1.2, 31-auth.md §2 and
§4.1 step 1: "authorization code + PKCE" against Keycloak's `fathom`
realm. `apps/web` never talks to Keycloak directly -- it has no client
secret and is not a public client either; the gateway is the confidential
client, so every one of these calls originates here, server-side.

Endpoint paths are Keycloak's own standard OIDC suffixes, appended to
`settings.oidc.issuer` (which already includes the realm segment, per
config.py's own docstring) -- no separate discovery-document fetch at
startup, since these paths are stable Keycloak conventions, not
per-deployment configuration.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class PkceChallenge:
    verifier: str
    challenge: str
    challenge_method: str = "S256"


def generate_pkce() -> PkceChallenge:
    """RFC 7636. `verifier` is the secret held server-side (in the
    short-lived login cookie); `challenge` is what Keycloak sees."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return PkceChallenge(verifier=verifier, challenge=challenge)


def generate_state() -> str:
    """Anti-forgery `state`, per 30-gateway.md §8.1.2's own login row."""
    return secrets.token_urlsafe(24)


def principal_id_from_access_token(access_token: str) -> str:
    """[PLACEHOLDER, matches the upstream side's own placeholder] Extracts
    the `sub` claim from the access token's JWT payload segment WITHOUT
    signature verification -- a real `X-Fathom-Principal`-style forward
    needs 31-auth.md's full ABAC-attribute-extraction pipeline, not built
    in this vertical slice on either side of the gateway boundary:
    `packages/py-common/src/fathom_py_common/authz.py::current_principal`
    (what every domain service, including PdM, actually checks today) is
    itself a stand-in that reads a raw `X-Fathom-Principal` header, not a
    verified bearer token -- forwarding this token as `Authorization:
    Bearer` would do nothing there. Re-verifying the signature here would
    also be redundant work in this specific position: this token was never
    presented by an untrusted caller, it came directly from Keycloak's own
    token endpoint over the confidential-client channel in
    `exchange_code()`, above.
    """
    try:
        _header, payload, _signature = access_token.split(".")
        padded = payload + "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        return str(claims["sub"])
    except (ValueError, KeyError) as exc:
        raise OidcClientError(f"access token is not a decodable JWT: {exc}") from exc


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    expires_in: int


class OidcClientError(Exception):
    """Raised when Keycloak's token endpoint rejects the exchange (e.g. a
    replayed or expired authorization code)."""


class OidcClient:
    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http_client

    def authorize_url(self, *, state: str, pkce: PkceChallenge) -> str:
        params = httpx.QueryParams(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "scope": "openid",
                "state": state,
                "code_challenge": pkce.challenge,
                "code_challenge_method": pkce.challenge_method,
            }
        )
        return f"{self._issuer}/protocol/openid-connect/auth?{params}"

    async def exchange_code(self, *, code: str, code_verifier: str) -> TokenResponse:
        """31-auth.md §4.1 step 1. No `offline_access` scope requested
        above, so Keycloak issues no refresh token -- 30-gateway.md
        §8.1.2's own invariant that `gateway_session` never holds one."""
        resp = await self._http.post(
            f"{self._issuer}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code_verifier": code_verifier,
            },
        )
        if resp.status_code != httpx.codes.OK:
            raise OidcClientError(f"token exchange failed: {resp.status_code} {resp.text}")
        body = resp.json()
        return TokenResponse(access_token=body["access_token"], expires_in=body["expires_in"])

    async def end_session(self, *, access_token: str) -> None:
        """Server-side session termination -- 30-gateway.md §8.1.2's own
        logout row: "there is no client-side `end_session_endpoint`
        redirect, because the browser holds no `id_token`." Since no
        refresh token is ever held either (§8.1.2's own invariant), this
        uses RFC 7009 token revocation on the access token itself, not
        Keycloak's `/logout` endpoint (which expects a refresh token to
        revoke) -- the standards-based mechanism available with only what
        this service actually holds. Failures are not raised: the LOCAL
        session is destroyed by the caller regardless (§8.1.2)."""
        await self._http.post(
            f"{self._issuer}/protocol/openid-connect/revoke",
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "token": access_token,
                "token_type_hint": "access_token",
            },
        )
