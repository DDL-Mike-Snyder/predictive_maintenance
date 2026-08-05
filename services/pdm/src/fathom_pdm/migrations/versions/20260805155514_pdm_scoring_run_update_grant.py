"""pdm scoring_run UPDATE grant

Revision ID: 17c852f3210f
Revises: ad1c64fd7fde
Create Date: 2026-08-05 15:55:14.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '17c852f3210f'
down_revision: str | None = 'ad1c64fd7fde'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # [CORRECTION, found deploying to a real AWS EKS cluster and running the
    # real Domino Job entrypoint against it for the first time -- the
    # first exercise of bulk_ingest_predictions() end to end under the
    # actual fathom_pdm_serving role. Every earlier real-Postgres test
    # exercised RLS on pdm.prediction, the model-binding tables, or the
    # event consumers -- none of them called bulk_ingest_predictions()
    # itself under this role.] `services/scoring.py`'s
    # `bulk_ingest_predictions()` updates the scoring_run row at the end
    # of every ingest (predictions_written, predictions_rejected, status,
    # completed_at) -- the initial migration granted this role SELECT and
    # INSERT on pdm.scoring_run, but never UPDATE. Same bug shape as bug
    # #11 (HANDOFF.md): a real code path's privilege need, never actually
    # exercised under the real role until now.
    op.execute("GRANT UPDATE ON pdm.scoring_run TO fathom_pdm_serving")


def downgrade() -> None:
    op.execute("REVOKE UPDATE ON pdm.scoring_run FROM fathom_pdm_serving")
