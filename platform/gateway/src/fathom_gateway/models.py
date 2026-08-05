"""Document 30-gateway.md §8.1.2: the gateway's own server-side session
store -- a table in its own CloudNativePG database (DECISION G-5: no
Redis, no shared cache), on the identical precedent 09 §5.3 already set
for idempotency records."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GatewaySessionRow(Base):
    """§8.1.2, verbatim: `gateway_session(session_id, access_token,
    expires_at, created_at)`. `access_token` is the user's own OIDC access
    token, singular -- never a refresh token (none is ever requested), and
    never the exchanged delegation token of §5.3 (that one is minted per
    agent turn and never persisted anywhere, this table included)."""

    __tablename__ = "gateway_session"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
