"""pdm outbox relay: quarantine table + dedicated relay role

Revision ID: 0fbc46e02a26
Revises: 17c852f3210f
Create Date: 2026-08-05 17:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0fbc46e02a26"
down_revision: str | None = "17c852f3210f"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # 11-outbox-sync-library.md §2.5: rows that exceed max_attempts move
    # here instead of being deleted -- a quarantined row is an incident
    # (03 §15.2: a state change without its event), not routine cleanup.
    op.create_table(
        "outbox_quarantine",
        sa.Column("outbox_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("shard", sa.SmallInteger(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("outbox_id"),
    )

    # The initial migration's own comment (see its `GRANT INSERT ON outbox`
    # line) already named this role before it existed: "the outbox-draining
    # relay (not yet built) is a separate, more-privileged process/role
    # that reads unpublished rows and sets published_at." fathom_pdm_serving
    # deliberately keeps INSERT-only on outbox -- the API-serving path must
    # never be the thing that also drains it.
    op.execute("CREATE ROLE fathom_pdm_relay")
    op.execute("GRANT USAGE ON SCHEMA public TO fathom_pdm_relay")
    op.execute("GRANT SELECT, UPDATE ON outbox TO fathom_pdm_relay")
    op.execute("GRANT INSERT ON outbox_quarantine TO fathom_pdm_relay")


def downgrade() -> None:
    op.execute("REVOKE ALL ON outbox_quarantine FROM fathom_pdm_relay")
    op.execute("REVOKE ALL ON outbox FROM fathom_pdm_relay")
    op.execute("DROP ROLE fathom_pdm_relay")
    op.drop_table("outbox_quarantine")
