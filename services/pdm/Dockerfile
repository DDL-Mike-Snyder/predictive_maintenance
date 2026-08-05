# syntax=docker/dockerfile:1.10
# ---------- stage 1: build ----------
FROM python:3.12-slim-bookworm@sha256:3f9c7f75b916e8279e24136d7a57769aba9e193715be52570417698c52d6eed0 AS builder

ARG PIP_INDEX_URL                      # private index; no public PyPI at build time in air-gapped builds
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.5@sha256:7bff3c3776ec467fc1437960f2c469d8beb30f536a6465a3350c647ccd260ec2 /uv /usr/local/bin/uv

# services/pdm/pyproject.toml's [tool.uv.sources] locates the four shared
# packages via `../../packages/<name>` (relative to services/pdm/), so the
# builder tree mirrors that same two-level depth (/build/services/pdm) --
# a flat /build would make uv try to normalize a path above the container's
# filesystem root and fail before any source is even copied in.
WORKDIR /build/services/pdm

# Dependencies first, from the lockfile only, so the layer caches independently
# of the SERVICE'S OWN source. `--no-install-project` skips building fathom-pdm
# itself, but PdM's four dependencies below are local editable path packages,
# not PyPI wheels -- uv has no wheel to fetch for them and must build them from
# real source even in this "deps only" pass, so (unlike the skeleton's
# canonical example, which assumes registry-hosted deps) their source has to
# be present before this RUN, not after. PdM depends on four such packages
# (services/pdm/pyproject.toml [tool.uv.sources]), one more than the
# skeleton's example: canonical-schemas, contracts, py-common, py-sync.
COPY services/pdm/pyproject.toml services/pdm/uv.lock ./
COPY packages/canonical-schemas /build/packages/canonical-schemas
COPY packages/contracts         /build/packages/contracts
COPY packages/py-common         /build/packages/py-common
COPY packages/py-sync           /build/packages/py-sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --no-editable

# Then the service source -- changes here don't bust the dependency layer above.
COPY services/pdm/src           /build/services/pdm/src
COPY services/pdm/alembic.ini   /build/services/pdm/alembic.ini

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Two build-vs-runtime path pitfalls fixed above, both from copying a venv
# built at one absolute path into an image where that path doesn't exist:
#  1. UV_PROJECT_ENVIRONMENT pins the venv to /app/.venv even though the
#     project root is /build/services/pdm: uv's console-script shims (e.g.
#     .venv/bin/uvicorn) get a shebang hard-coded to the venv's absolute path
#     at creation time, so unless the venv is built at the exact absolute
#     path it will occupy at runtime, the copied shim is unexecutable
#     ("No such file or directory", from a shebang pointing at a builder-only
#     path absent from the runtime image).
#  2. `--no-editable` on both syncs: by default uv installs local path
#     dependencies (this project and its four fathom-* packages) as editable
#     links pointing at their *build-time* source directories
#     (/build/packages/<name>, /build/services/pdm). Those directories don't
#     exist in the runtime image (only /app/.venv and /app/src are copied
#     over), so an editable install resolves to nothing at runtime
#     (`ModuleNotFoundError: No module named 'fathom_pdm'`). `--no-editable`
#     makes uv copy the real package files into site-packages instead of
#     linking to them, which is also the correct mode for a production image
#     regardless of the cross-stage-path issue.

# ---------- stage 2: runtime ----------
FROM python:3.12-slim-bookworm@sha256:3f9c7f75b916e8279e24136d7a57769aba9e193715be52570417698c52d6eed0 AS runtime

# Non-root, fixed numeric UID so the PodSecurityContext can assert it.
RUN groupadd --gid 65532 nonroot && \
    useradd  --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin nonroot

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_INDEX=1 \
    UV_NO_INDEX=1

WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv                      /app/.venv
COPY --from=builder --chown=root:root /build/services/pdm/src         /app/src
COPY --from=builder --chown=root:root /build/services/pdm/alembic.ini /app/alembic.ini

USER 65532:65532
EXPOSE 8000

# No HEALTHCHECK: Kubernetes probes own liveness and readiness (§5.6).
# No ENTRYPOINT shell wrapper: exec form so SIGTERM reaches uvicorn for graceful drain.
CMD ["uvicorn", "fathom_pdm.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--http", "httptools", \
     "--no-server-header", "--timeout-graceful-shutdown", "25"]
