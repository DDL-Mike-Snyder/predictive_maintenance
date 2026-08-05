"""pdm model binding (#27)

Revision ID: ad1c64fd7fde
Revises: 22ca49ca2ede
Create Date: 2026-08-05 14:19:53.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'ad1c64fd7fde'
down_revision: str | None = '22ca49ca2ede'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Creation order matters: model_binding.label_set_id FKs to label_set,
    # label_set.propensity_model_id FKs to propensity_model.
    op.create_table('propensity_model',
    sa.Column('propensity_model_id', sa.UUID(), nullable=False),
    sa.Column('spec_version', sa.String(), nullable=False),
    sa.Column('fitted_on_label_set', sa.UUID(), nullable=True),
    sa.Column('grid', sa.String(), nullable=False),
    sa.Column('policy_version_strata', postgresql.ARRAY(sa.String()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('fit_artifact_uri', sa.String(), nullable=False),
    sa.Column('positivity_min_k', sa.Numeric(), nullable=False),
    sa.Column('ess', sa.Numeric(), nullable=False),
    sa.Column('max_stabilized_weight', sa.Numeric(), nullable=False),
    sa.Column('mean_stabilized_weight', sa.Numeric(), nullable=False),
    sa.Column('calibration_of_propensity', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('pms_sensitivity', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('accepted', sa.Boolean(), nullable=False),
    sa.Column('rejection_reason', sa.String(), nullable=True),
    sa.Column('fitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('propensity_model_id'),
    schema='pdm'
    )
    op.create_table('label_set',
    sa.Column('label_set_id', sa.UUID(), nullable=False),
    sa.Column('equipment_family', sa.String(), nullable=False),
    sa.Column('taxonomy_version', sa.String(), nullable=False),
    sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('grid', sa.String(), nullable=False),
    sa.Column('stratum', sa.String(), nullable=False),
    sa.Column('propensity_model_id', sa.UUID(), nullable=True),
    sa.Column('artifact_uri', sa.String(), nullable=False),
    sa.Column('feature_definition_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('feature_data_time_max', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ipcw_summary', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('built_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('classification', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.CheckConstraint("stratum IN ('treated','policy_frozen','combined')", name='label_set_stratum'),
    sa.ForeignKeyConstraint(['propensity_model_id'], ['pdm.propensity_model.propensity_model_id'], ),
    sa.PrimaryKeyConstraint('label_set_id'),
    schema='pdm'
    )
    op.create_table('model_binding',
    sa.Column('binding_id', sa.UUID(), nullable=False),
    sa.Column('tier', sa.SmallInteger(), nullable=False),
    sa.Column('equipment_family', sa.String(), nullable=False),
    sa.Column('taxonomy_version', sa.String(), nullable=False),
    sa.Column('registry_model_version', sa.String(), nullable=False),
    sa.Column('registry_model_uri', sa.String(), nullable=False),
    sa.Column('approval_ref', sa.String(), nullable=False),
    sa.Column('label_set_id', sa.UUID(), nullable=False),
    sa.Column('censoring_correction', sa.String(), nullable=False),
    sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("censoring_correction IN ('ipcw_stabilized')", name='model_binding_censoring_correction'),
    sa.CheckConstraint('tier BETWEEN 0 AND 3', name='model_binding_tier_range'),
    sa.ForeignKeyConstraint(['label_set_id'], ['pdm.label_set.label_set_id'], ),
    sa.PrimaryKeyConstraint('binding_id'),
    sa.UniqueConstraint('tier', 'equipment_family', 'taxonomy_version', 'activated_at'),
    schema='pdm'
    )

    # --- Grants, scoped to what the code this migration ships with actually
    # does (22-pdm.md HANDOFF bug #11: a newly created table grants nothing
    # beyond its owner by default; budget for this sweep up front rather
    # than discovering the gap by connecting as the role later). This
    # service's own code only ever READS propensity_model/label_set (the
    # §5.6 refusal checks); it reads, inserts, and updates model_binding
    # (create, activate, and superseding a previously-active binding).
    op.execute("GRANT SELECT ON pdm.propensity_model TO fathom_pdm_serving")
    op.execute("GRANT SELECT ON pdm.label_set TO fathom_pdm_serving")
    op.execute("GRANT SELECT, INSERT, UPDATE ON pdm.model_binding TO fathom_pdm_serving")
    # [CORRECTION, found the same way bug #11 was: connecting as
    # fathom_pdm_serving instead of the owner for the first time.]
    # pdm.calibration_record itself predates this migration (the initial
    # migration's own grant sweep covered scoring_run/prediction_provenance/
    # criticality_assessment, but never calibration_record -- nothing read
    # it through the ORM before §5.6's "a calibration record exists /
    # powered" refusal checks, this migration's own reason for existing).
    # Granted here, not backported into the initial migration, so this
    # file's history says what actually happened: the gap was latent from
    # the start, and this is the point it was found and closed.
    op.execute("GRANT SELECT ON pdm.calibration_record TO fathom_pdm_serving")

    # [CORRECTION, second one found the same way, same session: activating
    # a binding publishes `model_binding.activated` -- the first code path
    # in this whole codebase that calls `OutboxWriter.emit()` under the
    # real `fathom_pdm_serving` role rather than SQLite or the
    # migration-owning superuser (`bulk_ingest_predictions` already
    # published events, but only ever under sqlite or as owner in every
    # test written before this one). Postgres requires sequence USAGE to
    # fire an autoincrement column's own `nextval()` DEFAULT during INSERT,
    # independent of `fathom_sync.OutboxRow`'s now-disabled implicit
    # RETURNING (see that model's own comment) -- INSERT on the table alone
    # was never sufficient, for any service, since the initial migration
    # first granted it. `outbox_outbox_id_seq` is the sequence Postgres
    # auto-names for `outbox.outbox_id`'s identity column.
    op.execute("GRANT USAGE ON SEQUENCE outbox_outbox_id_seq TO fathom_pdm_serving")


def downgrade() -> None:
    op.execute("REVOKE USAGE ON SEQUENCE outbox_outbox_id_seq FROM fathom_pdm_serving")
    op.execute("REVOKE ALL ON pdm.calibration_record FROM fathom_pdm_serving")
    op.execute("REVOKE ALL ON pdm.model_binding FROM fathom_pdm_serving")
    op.execute("REVOKE ALL ON pdm.label_set FROM fathom_pdm_serving")
    op.execute("REVOKE ALL ON pdm.propensity_model FROM fathom_pdm_serving")

    op.drop_table('model_binding', schema='pdm')
    op.drop_table('label_set', schema='pdm')
    op.drop_table('propensity_model', schema='pdm')
