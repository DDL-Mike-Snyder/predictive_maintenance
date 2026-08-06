"""`config.py` is the ONLY module in this service that reads the
environment. Everything else takes `Settings` by dependency injection.
Document 09 §4.5."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    log_level: str = "INFO"
    # [ADDITIVE, opt-in] When set, main.py mounts apps/web's own build
    # (its `dist/` directory) and serves it same-origin from this same
    # process -- the Domino-App-hosting path. `None` (the default) leaves
    # every existing local/dev deployment (a separately-run `vite dev`
    # server) completely unaffected; nothing about the current working
    # setup changes unless this is explicitly set.
    static_dir: str | None = None


class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = 10
    max_overflow: int = 5


class OidcSettings(BaseModel):
    """31-auth.md §2's Keycloak binding. `issuer` already includes the
    realm segment (`https://<host>/realms/fathom`), matching every other
    service's own `auth.issuer` setting (e.g. services/pdm/.env.example) --
    endpoint paths are derived by appending Keycloak's standard
    `/protocol/openid-connect/*` suffixes to it, not by templating a
    separate realm name in. `client_secret` is the gateway's own
    confidential-client credential -- apps/web never talks to Keycloak
    directly, per 30-gateway.md §8.1.2's own reasoning."""

    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str


class SessionSettings(BaseModel):
    """30-gateway.md §8.1.2. `cookie_signing_key` signs the short-lived
    PKCE/state cookie `/session/login` sets -- distinct from the
    server-side `gateway_session` row itself, which needs no signature
    since its value is an opaque id looked up in the database, not trusted
    client-side state."""

    cookie_signing_key: str
    session_ttl_seconds: int = 28800  # 8h, 31-auth.md's own default extended-identity window
    landing_url: str = "/"


class OtelSettings(BaseModel):
    enabled: bool = False


class PdmUpstreamSettings(BaseModel):
    """[SCOPE -- see this service's own CLAUDE.md entry] The pass-through
    surface (30-gateway.md §8.2, DECISION G-3) is nine sub-applications
    plus platform services in the real spec; this vertical slice proxies
    only `pdm`, the one real backend that exists. base_url plus the path
    to its committed openapi.json (09 §4.2's monorepo layout) are both
    needed to generate routes at startup."""

    base_url: str
    openapi_path: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FATHOM_", env_nested_delimiter="__", extra="forbid"
    )

    app: AppSettings = AppSettings()
    database: DatabaseSettings
    oidc: OidcSettings
    session: SessionSettings
    otel: OtelSettings = OtelSettings()
    pdm: PdmUpstreamSettings
