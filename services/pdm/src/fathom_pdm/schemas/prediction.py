"""Wire request/response models specific to PdM. Canonical kernel types are
IMPORTED from `packages/canonical-schemas`, never redefined (09 §4.1)."""

from __future__ import annotations

import uuid

from fathom_schemas import FailurePrediction, FathomModel


class BulkPredictionIngestRequest(FathomModel):
    """22-pdm.md §2.5: 'The bulk ingest schema does NOT contain
    `serving_class` -- a caller cannot set it, cannot override it.'"""

    predictions: tuple[FailurePrediction, ...]


class BulkPredictionIngestResult(FathomModel):
    scoring_run_id: uuid.UUID
    predictions_written: int
    predictions_rejected: int
    rejection_summary: tuple[str, ...] = ()
