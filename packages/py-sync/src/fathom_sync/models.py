"""SQLAlchemy 2.0 declarative models for the outbox, inbox, and per-producer
sequence tables. Document 11 §2 (outbox), §3 (inbox), §4.3 (sequencer).

These tables live in the OWNING SERVICE's own database -- never a shared
sync database (11 §2.2: "there is no atomic two-database commit here, and
there will not be one"). A service includes this module's `Base.metadata`
in its own Alembic env so these tables are created alongside its domain
tables in the same migration history.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Postgres in production (09-monorepo-and-conventions.md §2.1: "PostgreSQL via
# CloudNativePG, database-per-service"), portable JSON elsewhere so the unit
# test suite can run against SQLite without a container. UUID columns are
# plain String -- every caller already passes str(uuid), and a portable
# String avoids the same dialect-compilation trap JSONB has on SQLite.
_JsonVariant = JSON().with_variant(JSONB(), "postgresql")

# SQLite's autoincrement rowid alias only engages for a literal INTEGER
# PRIMARY KEY column; BigInteger compiles to BIGINT there and the alias
# never applies. Postgres gets the real bigint identity column either way.
_BigIdentity = Integer().with_variant(BigInteger(), "postgresql")


class Base(DeclarativeBase):
    pass


class OutboxRow(Base):
    """Document 11 §2.2. One row per emitted event, written in the SAME
    transaction as the domain state change it announces."""

    __tablename__ = "outbox"

    outbox_id: Mapped[int] = mapped_column(_BigIdentity, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)

    producer_slug: Mapped[str] = mapped_column(String, nullable=False)
    producer_version: Mapped[str] = mapped_column(String, nullable=False)
    producer_node_id: Mapped[str] = mapped_column(String, nullable=False)
    monotonic_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hlc_physical_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hlc_logical: Mapped[int] = mapped_column(Integer, nullable=False)
    hlc_node_id: Mapped[str] = mapped_column(String, nullable=False)

    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    partition_key: Mapped[str] = mapped_column(String, nullable=False)
    compaction_key: Mapped[str | None] = mapped_column(String, nullable=True)
    aggregate: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String, nullable=False)

    scope: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    baseline_epoch: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    replay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingest_time: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_quality: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)

    payload_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    payload_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload_kek_id: Mapped[str] = mapped_column(String, nullable=False)

    record_signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(String, nullable=False)

    shard: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_until_mono: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acked_by_shore_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("producer_slug", "producer_node_id", "monotonic_seq", name="outbox_seq_unique"),
        CheckConstraint(
            "payload_ciphertext IS NOT NULL OR payload_ref IS NOT NULL",
            name="outbox_payload_present",
        ),
        CheckConstraint(
            "compaction_key IS NULL OR compaction_key <> partition_key",
            name="outbox_compaction_key_distinct",
        ),
        Index("outbox_unpublished", "shard", "outbox_id", postgresql_where="published_at IS NULL"),
        Index("outbox_prunable", "published_at", postgresql_where="published_at IS NOT NULL"),
        # [CORRECTION, found while building services/pdm's model-binding
        # activation against the real `fathom_pdm_serving` role for the
        # first time -- the first code path to actually call `emit()`
        # under that role rather than sqlite or the migration-owning
        # superuser.] SQLAlchemy's Postgres dialects default to fetching an
        # autoincrement PK back via an implicit `RETURNING outbox_id`
        # after INSERT. Every service's own migration grants this role
        # INSERT ONLY on its outbox table, by design (11 §2.2: "it never
        # publishes... the relay's job" -- the writer must not also be able
        # to read pending rows). `RETURNING` a column requires the same
        # privilege as `SELECT`ing it, so every INSERT would fail with
        # "permission denied for table outbox" under that intentionally
        # narrower grant -- and nothing in `emit()`'s own return value
        # (`EventId` carries only the client-generated `event_id`, never
        # `outbox_id`) ever uses the value RETURNING would fetch anyway.
        # `implicit_returning=False` turns that fetch off at the source,
        # for every service that imports this table, not just PdM's.
        {"implicit_returning": False},
    )


class InboxRow(Base):
    """Document 11 §3.1. `event_id` is recorded and the resulting state
    change is applied IN ONE TRANSACTION. Only rows with `processed_at` set
    suppress redelivery -- recording receipt before processing is prohibited."""

    __tablename__ = "inbox"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    producer_slug: Mapped[str] = mapped_column(String, nullable=False)
    producer_node_id: Mapped[str] = mapped_column(String, nullable=False)
    monotonic_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    aggregate: Mapped[str] = mapped_column(String, nullable=False)

    topic: Mapped[str] = mapped_column(String, nullable=False)
    kafka_partition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kafka_offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingest_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_quality: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)

    processed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    blocked_on_epoch: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    blocked_since_mono: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    replay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "producer_slug", "producer_node_id", "monotonic_seq", name="inbox_seq_unique"
        ),
        Index("inbox_unprocessed", "received_at", postgresql_where="processed_at IS NULL"),
        Index("inbox_blocked", "blocked_on_epoch", postgresql_where="blocked_on_epoch IS NOT NULL"),
    )


class ProducerSequenceRow(Base):
    """Document 11 §4.3. Gap-free, strictly increasing sequence per
    (producer_slug, producer_node_id), allocated inside the caller's
    transaction. A row-lock counter, never a native Postgres SEQUENCE --
    native sequences leak values on rollback, breaking gap-freedom."""

    __tablename__ = "producer_sequence"

    producer_slug: Mapped[str] = mapped_column(String, primary_key=True)
    producer_node_id: Mapped[str] = mapped_column(String, primary_key=True)
    next_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    __table_args__ = (PrimaryKeyConstraint("producer_slug", "producer_node_id"),)


class RemediatedSelectorRow(Base):
    """Document 11 §3.7. One row per selector affected by an applied
    remediation event, consulted before materializing any read-model row a
    live apply or a changed_since rebuild would otherwise write."""

    __tablename__ = "remediated_selectors"

    selector_hash: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    remediation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    applied_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
