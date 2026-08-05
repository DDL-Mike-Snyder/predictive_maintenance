"""SQLAlchemy 2.0 `DeclarativeBase` mapped classes. Document 09 §4.1: private
to this service, never serialized to the wire directly [03 principle 1].

Scope of this vertical slice (not the full 22-pdm.md surface): `scoring_run`,
`prediction` (with the RLS holdout mechanism), `criticality_assessment`,
`tier_policy`, `calibration_record`, `prediction_provenance`. Omitted for
now: `label_set`/`label_observation`/`propensity_model`/`model_binding` --
the IPCW/propensity-model fitting pipeline, which is a substantial second
vertical slice of its own and not needed to prove the scaffold pattern this
pass validates (API layer, RLS, outbox, calibration gate, Domino Job
integration).
"""

from fathom_sync import Base as SyncBase
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Every service includes the shared py-sync tables (outbox, inbox,
# producer_sequence, remediated_selectors) in its OWN migration history
# (11-outbox-sync-library.md §2.2: "there is no atomic two-database commit
# here, and there will not be one").
SYNC_TABLES = SyncBase.metadata.tables

# Import every model module so its table registers against Base.metadata --
# required for Alembic autogenerate and for `Base.metadata.create_all()` in
# tests. Imported at the bottom to avoid a circular import (each model
# module does `from . import Base`).
from .calibration import CalibrationRecord  # noqa: E402
from .criticality import CriticalityAssessment  # noqa: E402
from .prediction import Prediction  # noqa: E402
from .provenance import PredictionProvenance  # noqa: E402
from .scoring_run import ScoringRun  # noqa: E402
from .tier_policy import TierPolicy  # noqa: E402

__all__ = [
    "SYNC_TABLES",
    "Base",
    "CalibrationRecord",
    "CriticalityAssessment",
    "Prediction",
    "PredictionProvenance",
    "ScoringRun",
    "TierPolicy",
]
