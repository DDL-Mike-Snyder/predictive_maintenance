"""Cursor pagination and `changed_since` reads. Document 03 §4, obligation 5, D5.

Neither `10-shared-packages.md` nor `09-monorepo-and-conventions.md` gives a
literal implementation for `Page[T]`/`CursorParams`/`ChangedSinceParams`
despite both citing them as shared -- authored here from the prose contract:
opaque base64url cursor over a stable sort key, `next_cursor` in the body,
no total count on unbounded collections.
"""

from __future__ import annotations

import base64
import json
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


def encode_cursor(sort_key: object) -> str:
    payload = json.dumps({"k": sort_key}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str) -> object:
    padded = cursor + "=" * (-len(cursor) % 4)
    payload = base64.urlsafe_b64decode(padded.encode())
    return json.loads(payload)["k"]


class CursorParams(BaseModel):
    limit: int = 50
    cursor: str | None = None

    @classmethod
    def as_query(
        cls, limit: int = Query(default=50, ge=1, le=500), cursor: str | None = Query(default=None)
    ) -> "CursorParams":
        return cls(limit=limit, cursor=cursor)


class Page(BaseModel, Generic[T]):
    """No total count on unbounded collections -- document 03 §4."""

    items: list[T]
    next_cursor: str | None = None


class ChangedSinceParams(BaseModel):
    """Every aggregate a declared consumer projects exposes a read
    accepting this. Document 03 §4, obligation 5, D5. `changed_since`
    accepts a `rt:<seq>` cursor-form value OR an RFC 3339 timestamp,
    translated ONCE to a `record_seq` watermark -- never re-derived, and
    never itself the ordering key (that is always `record_seq`)."""

    changed_since: str | None = None
    cursor: str | None = None
    limit: int = 100

    @classmethod
    def as_query(
        cls,
        changed_since: str | None = Query(default=None),
        cursor: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> "ChangedSinceParams":
        return cls(changed_since=changed_since, cursor=cursor, limit=limit)
