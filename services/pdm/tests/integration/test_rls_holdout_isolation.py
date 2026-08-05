"""RLS enforcement against real PostgreSQL. Document 22-pdm.md §4.5's
holdout isolation mechanism (mechanism 3 of 5: "the mechanism that survives
a refactor").

SQLite cannot express row-level security at all (see `PredictionRepository`'s
own docstring), so this is the *only* place these policies are exercised
against a real engine rather than just reviewed as DDL. It runs the actual
Alembic migration -- not a hand-rolled schema -- so a drift between the
migration and the spec's DDL would be caught here too.

Deliberately bypasses the ORM and SQLAlchemy entirely: two dedicated
PostgreSQL login roles (test-local; provisioning real login credentials for
`fathom_pdm_serving`/`fathom_pdm_research` is a deployment/secrets concern,
not something a migration should do) connect directly via psycopg and issue
raw SQL, so a passing test proves the *database* enforces isolation
independent of anything the application layer does or forgets to do.

[NOTE -- real bug found while writing this test.] Both `CREATE ROLE
fathom_pdm_serving`/`fathom_pdm_research` in 22-pdm.md §4.5 and this
service's migration granted table-level privileges but never `GRANT USAGE
ON SCHEMA pdm`. PostgreSQL checks schema USAGE before object-level
privileges, so every query either role issued failed with "permission
denied for schema pdm" -- confirmed against a real container, then fixed in
both the spec and the migration. Not a security hole (fails closed), but it
would have made the whole mechanism silently unusable rather than merely
under-tested.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

_SERVICE_ROOT = Path(__file__).resolve().parents[2]

_ENV_DEFAULTS = {
    "FATHOM_EVENTS__BROKERS": "test-broker:9093",
    "FATHOM_EVENTS__SCHEMA_REGISTRY": "http://test-schema-registry",
    "FATHOM_AUTH__ISSUER": "https://test-issuer",
    "FATHOM_AUTH__JWKS_URL": "https://test-issuer/jwks",
    "FATHOM_AUDIT__BASE_URL": "http://test-audit",
    "FATHOM_REFERENCE_DATA__BASE_URL": "http://test-reference-data",
}


@pytest.fixture(scope="module")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:16-alpine",
        dbname="pdm",
        username="pdm_owner",
        password="pdm_owner",  # noqa: S106 -- throwaway, ephemeral testcontainer
    ) as pg:
        yield pg


@pytest.fixture(scope="module")
def owner_dsn(pg_container: PostgresContainer) -> str:
    """Runs the real Alembic migration against the container, then returns
    a plain `postgresql://` DSN for the bootstrap (superuser) role -- the
    official postgres image's `POSTGRES_USER` is always a superuser, so it
    bypasses RLS regardless of `FORCE ROW LEVEL SECURITY`. That's fine here:
    seeding fixture data is not the behavior under test."""
    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    async_url = f"postgresql+asyncpg://pdm_owner:pdm_owner@{host}:{port}/pdm"

    prior = os.environ.get("FATHOM_DATABASE__URL")
    os.environ["FATHOM_DATABASE__URL"] = async_url
    for key, value in _ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    try:
        cfg = Config(str(_SERVICE_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(_SERVICE_ROOT / "src/fathom_pdm/migrations"))
        command.upgrade(cfg, "head")
    finally:
        if prior is None:
            os.environ.pop("FATHOM_DATABASE__URL", None)
        else:
            os.environ["FATHOM_DATABASE__URL"] = prior

    return f"postgresql://pdm_owner:pdm_owner@{host}:{port}/pdm"


@pytest.fixture(scope="module")
def rls_roles(owner_dsn: str) -> Iterator[dict[str, str]]:
    """Two throwaway login roles, each granted membership in one of the two
    RLS group roles the migration creates -- standing in for the real
    per-pool service credentials a deployment would provision."""
    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE ROLE test_serving_login LOGIN PASSWORD 'serving'")
        cur.execute("GRANT fathom_pdm_serving TO test_serving_login")
        cur.execute("CREATE ROLE test_research_login LOGIN PASSWORD 'research'")
        cur.execute("GRANT fathom_pdm_research TO test_research_login")

    host_port_db = owner_dsn.split("@", 1)[1]
    yield {
        "serving": f"postgresql://test_serving_login:serving@{host_port_db}",
        "research": f"postgresql://test_research_login:research@{host_port_db}",
    }

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("REVOKE fathom_pdm_serving FROM test_serving_login")
        cur.execute("DROP ROLE test_serving_login")
        cur.execute("REVOKE fathom_pdm_research FROM test_research_login")
        cur.execute("DROP ROLE test_research_login")


def _seed_prediction(
    conn: psycopg.Connection, *, serving_class: str, status: str = "published"
) -> tuple[uuid.UUID, uuid.UUID]:
    """Inserts one scoring_run + one prediction_provenance + one prediction
    row (as the superuser, bypassing RLS) and returns
    (prediction_id, installed_item_id) for later assertions."""
    scoring_run_id = uuid.uuid4()
    provenance_id = uuid.uuid4()
    prediction_id = uuid.uuid4()
    installed_item_id = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pdm.scoring_run (
                scoring_run_id, stratum, trigger, scope, baseline_epoch_at_start,
                model_bindings, label_set_ids, feature_definition_time,
                domino_execution_ref, read_model_lag_at_start, status, classification
            ) VALUES (%s, 'operational', 'scheduled', '{}', '{}', '{}', '{}', now(),
                      'test-run', '{}', 'published', '{}')
            """,
            (scoring_run_id,),
        )
        cur.execute(
            """
            INSERT INTO pdm.prediction_provenance (
                provenance_id, scoring_run_id, model_binding_id, label_set_id,
                gate_decision, feature_observations, feature_definition_time,
                fallback_path, suppressed_factor_count, suppressed_factors,
                read_model_lag, classification
            ) VALUES (%s, %s, %s, %s, '{}', '{}', now(), '{}', 0, '[]', '{}', '{}')
            """,
            (provenance_id, scoring_run_id, uuid.uuid4(), uuid.uuid4()),
        )
        cur.execute(
            """
            INSERT INTO pdm.prediction (
                prediction_id, scoring_run_id, asset_id, installed_item_id, position_id,
                niin, equipment_family, baseline_id, baseline_epoch, horizon_days,
                p_failure, reference_class, sharpness, calibration_population,
                population_hazard_rate, confidence, fallback_level, tier,
                contributing_factors, model_version, computed_at, status,
                serving_class, provenance_id, classification
            ) VALUES (
                %s, %s, %s, %s, %s,
                '000000000', 'test-family', %s, 1, 30,
                0.1, 'class_estimate', 0.5, 100,
                0.01, 0.8, 0, 1,
                '[]', 'test-model-v1', now(), %s,
                %s, %s, '{}'
            )
            """,
            (
                prediction_id,
                scoring_run_id,
                uuid.uuid4(),
                installed_item_id,
                uuid.uuid4(),
                uuid.uuid4(),
                status,
                serving_class,
                provenance_id,
            ),
        )
    conn.commit()
    return prediction_id, installed_item_id


@pytest.fixture()
def seeded(owner_dsn: str) -> Iterator[dict[str, uuid.UUID]]:
    with psycopg.connect(owner_dsn) as conn:
        actionable_id, _ = _seed_prediction(conn, serving_class="actionable")
        research_id, _ = _seed_prediction(conn, serving_class="research_only")
        yield {"actionable": actionable_id, "research": research_id}
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pdm.prediction WHERE prediction_id IN (%s, %s)",
                (actionable_id, research_id),
            )
        conn.commit()


def test_rls_and_force_are_enabled(owner_dsn: str) -> None:
    with psycopg.connect(owner_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE oid = 'pdm.prediction'::regclass"
        )
        enabled, forced = cur.fetchone()
    assert (enabled, forced) == (True, True)


def test_serving_role_sees_only_actionable(
    rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    with psycopg.connect(rls_roles["serving"]) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT prediction_id FROM pdm.prediction WHERE prediction_id IN (%s, %s)",
            (seeded["actionable"], seeded["research"]),
        )
        visible = {row[0] for row in cur.fetchall()}
    assert visible == {seeded["actionable"]}


def test_research_role_sees_only_research_only(
    rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    with psycopg.connect(rls_roles["research"]) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT prediction_id FROM pdm.prediction WHERE prediction_id IN (%s, %s)",
            (seeded["actionable"], seeded["research"]),
        )
        visible = {row[0] for row in cur.fetchall()}
    assert visible == {seeded["research"]}


def test_research_role_has_no_write_access(
    rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    """13 §8.6's credential separation: the research role holds no INSERT/
    UPDATE/DELETE on any table, mirrored here as a hard permission-denied,
    not merely an RLS-filtered zero-row outcome."""
    with (
        psycopg.connect(rls_roles["research"]) as conn,
        conn.cursor() as cur,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        cur.execute(
            "UPDATE pdm.prediction SET status = 'invalidated' WHERE prediction_id = %s",
            (seeded["research"],),
        )


def test_serving_insert_rejects_disallowed_serving_class(
    owner_dsn: str, rls_roles: dict[str, str]
) -> None:
    """`serving_insert`'s WITH CHECK -- the row must be one of the two
    values `serving_insert` allows, not whatever a caller supplies."""
    with psycopg.connect(owner_dsn) as conn:
        scoring_run_id = uuid.uuid4()
        provenance_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pdm.scoring_run (
                    scoring_run_id, stratum, trigger, scope, baseline_epoch_at_start,
                    model_bindings, label_set_ids, feature_definition_time,
                    domino_execution_ref, read_model_lag_at_start, status, classification
                ) VALUES (%s, 'operational', 'scheduled', '{}', '{}', '{}', '{}', now(),
                          'test-run', '{}', 'published', '{}')
                """,
                (scoring_run_id,),
            )
            cur.execute(
                """
                INSERT INTO pdm.prediction_provenance (
                    provenance_id, scoring_run_id, model_binding_id, label_set_id,
                    gate_decision, feature_observations, feature_definition_time,
                    fallback_path, suppressed_factor_count, suppressed_factors,
                    read_model_lag, classification
                ) VALUES (%s, %s, %s, %s, '{}', '{}', now(), '{}', 0, '[]', '{}', '{}')
                """,
                (provenance_id, scoring_run_id, uuid.uuid4(), uuid.uuid4()),
            )
        conn.commit()

    try:
        with (
            psycopg.connect(rls_roles["serving"]) as conn,
            conn.cursor() as cur,
            pytest.raises(psycopg.errors.InsufficientPrivilege),
        ):
            cur.execute(
                """
                INSERT INTO pdm.prediction (
                    prediction_id, scoring_run_id, asset_id, installed_item_id, position_id,
                    niin, equipment_family, baseline_id, baseline_epoch, horizon_days,
                    p_failure, reference_class, sharpness, calibration_population,
                    population_hazard_rate, confidence, fallback_level, tier,
                    contributing_factors, model_version, computed_at, status,
                    serving_class, provenance_id, classification
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    '000000000', 'test-family', %s, 1, 30,
                    0.1, 'class_estimate', 0.5, 100,
                    0.01, 0.8, 0, 1,
                    '[]', 'test-model-v1', now(), 'published',
                    'holdout_bypass_attempt', %s, '{}'
                )
                """,
                (
                    uuid.uuid4(),
                    scoring_run_id,
                    uuid.uuid4(),
                    uuid.uuid4(),
                    uuid.uuid4(),
                    uuid.uuid4(),
                    provenance_id,
                ),
            )
    finally:
        with psycopg.connect(owner_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pdm.prediction_provenance WHERE provenance_id = %s", (provenance_id,)
            )
            cur.execute("DELETE FROM pdm.scoring_run WHERE scoring_run_id = %s", (scoring_run_id,))
            conn.commit()


def test_serving_role_has_no_direct_update_grant(
    rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    """[CORRECTION] A prior revision of this test proved a plain `UPDATE`
    under `fathom_pdm_serving` reaches a research_only row via a
    `serving_invalidate` policy with `USING (true)`. It does not: PostgreSQL
    requires an UPDATE's targeted rows to also satisfy the role's SELECT
    policy (the WHERE clause is itself a read), so `actionable_read` vetoes
    the UPDATE regardless of what an UPDATE-scoped policy says -- confirmed
    empirically, and the reason this role now holds no UPDATE grant on the
    table at all. Even an actionable row -- one this role CAN see -- must be
    unreachable by a plain UPDATE, since the grant itself is gone."""
    with (
        psycopg.connect(rls_roles["serving"]) as conn,
        conn.cursor() as cur,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        cur.execute(
            "UPDATE pdm.prediction SET status = 'invalidated' WHERE prediction_id = %s",
            (seeded["actionable"],),
        )


def test_invalidate_prediction_reaches_research_only_rows(
    owner_dsn: str, rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    """The actual mechanism: `pdm.invalidate_prediction()`, a SECURITY
    DEFINER function owned by the BYPASSRLS `fathom_pdm_invalidator` role,
    EXECUTE-granted to `fathom_pdm_serving`. Must reach a research_only row
    -- the one thing a real RLS policy on this role could never do."""
    with psycopg.connect(rls_roles["serving"]) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT pdm.invalidate_prediction(%s, 'test')",
            (seeded["research"],),
        )
        (found,) = cur.fetchone()
        conn.commit()
    assert found is True

    with psycopg.connect(owner_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, invalidation_cause FROM pdm.prediction WHERE prediction_id = %s",
            (seeded["research"],),
        )
        status, cause = cur.fetchone()
    assert (status, cause) == ("invalidated", "test")


def test_invalidate_prediction_reaches_actionable_rows_too(
    owner_dsn: str, rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    """The same function is the only invalidation path for actionable rows
    too, now that `fathom_pdm_serving` holds no UPDATE grant at all."""
    with psycopg.connect(rls_roles["serving"]) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT pdm.invalidate_prediction(%s, 'test')",
            (seeded["actionable"],),
        )
        (found,) = cur.fetchone()
        conn.commit()
    assert found is True

    with psycopg.connect(owner_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM pdm.prediction WHERE prediction_id = %s", (seeded["actionable"],)
        )
        (status,) = cur.fetchone()
    assert status == "invalidated"


def test_invalidate_prediction_returns_false_for_unknown_id(rls_roles: dict[str, str]) -> None:
    with psycopg.connect(rls_roles["serving"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT pdm.invalidate_prediction(%s, 'test')", (uuid.uuid4(),))
        (found,) = cur.fetchone()
    assert found is False


def test_research_role_cannot_call_invalidate_prediction(
    rls_roles: dict[str, str], seeded: dict[str, uuid.UUID]
) -> None:
    """EXECUTE is granted to `fathom_pdm_serving` only -- the research role,
    which holds no write access anywhere, must not be able to invoke this
    either, even though the function itself bypasses RLS once inside."""
    with (
        psycopg.connect(rls_roles["research"]) as conn,
        conn.cursor() as cur,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        cur.execute("SELECT pdm.invalidate_prediction(%s, 'test')", (seeded["research"],))
