"""`ETag` / `If-Match`. Document 03 §4, §7.2, D16.

ETag is derived from a monotonic `version` integer column on the aggregate
root, rendered `W/"<version>"` [ESTABLISHED HERE] -- a content hash would
change when an unrelated denormalized field changed and would produce
spurious 412s; a version column makes the concurrency check a single
`WHERE version = :expected` predicate.
"""

from __future__ import annotations

from fastapi import Header

from .problems import ProblemException


def etag_for(version: int) -> str:
    return f'W/"{version}"'


def require_if_match(if_match: str | None = Header(default=None, alias="If-Match")) -> int:
    """Returns the expected version. `428` if the header is absent, `400`
    if malformed. Stricter than 03 §4's letter and deliberate -- D16 is that
    a missing claim/`If-Match` produces two approvals and two work orders."""
    if if_match is None:
        raise ProblemException(
            type="urn:fathom:problem:common:precondition-required",
            title="If-Match required",
            status=428,
            detail="PUT, PATCH, and proposal adjudication require If-Match (03 §4, §7.2, D16)",
        )
    stripped = if_match.strip()
    if stripped.startswith('W/"') and stripped.endswith('"'):
        stripped = stripped[3:-1]
    elif stripped.startswith('"') and stripped.endswith('"'):
        stripped = stripped[1:-1]
    try:
        return int(stripped)
    except ValueError:
        raise ProblemException(
            type="urn:fathom:problem:common:bad-request",
            title="Malformed If-Match",
            status=400,
            detail=f"could not parse a version from If-Match={if_match!r}",
        ) from None


class VersionConflict(ProblemException):
    """Raised by a repository's compare-and-swap
    (`UPDATE ... SET version = version + 1 WHERE id = :id AND version =
    :expected`) when zero rows are affected."""

    def __init__(self, *, resource: str, expected_version: int) -> None:
        super().__init__(
            type="urn:fathom:problem:common:version-conflict",
            title="Version conflict",
            status=412,
            detail=f"{resource} was modified since version {expected_version} was read",
            expected_version=expected_version,
        )
