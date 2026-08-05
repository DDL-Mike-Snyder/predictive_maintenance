"""`config.py` is the ONLY module in this service that reads the
environment. Everything else takes `Settings` by dependency injection.
Document 09 §4.5."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    log_level: str = "INFO"
    staleness_bound_seconds: int = 300


class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = 10
    max_overflow: int = 5


class EventsSettings(BaseModel):
    brokers: str
    schema_registry: str
    consumer_group: str = "fathom-pdm-v1"


class AuthSettings(BaseModel):
    issuer: str
    jwks_url: str


class AuditSettings(BaseModel):
    base_url: str


class ReferenceDataSettings(BaseModel):
    base_url: str


class OtelSettings(BaseModel):
    enabled: bool = False


class DominoSettings(BaseModel):
    api_host: str = ""
    project_id: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FATHOM_", env_nested_delimiter="__", extra="forbid"
    )

    app: AppSettings = AppSettings()
    database: DatabaseSettings
    events: EventsSettings
    auth: AuthSettings
    audit: AuditSettings
    reference_data: ReferenceDataSettings
    otel: OtelSettings = OtelSettings()
    domino: DominoSettings = DominoSettings()
