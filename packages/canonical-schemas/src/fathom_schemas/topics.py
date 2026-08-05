"""Topic and event-type naming grammar. Document 03 §5.1, §5.4 [C26].

`fathom.<slug>.<aggregate>.v<major>` for topics; `fathom.<slug>.<aggregate>.<verb>`
for event types (snake_case throughout).
"""

from __future__ import annotations

import re

from .slugs import AnySlug

_SLUG_RE = r"[a-z][a-z0-9-]*"
_AGGREGATE_RE = r"[a-z][a-z0-9_]*"
_VERB_RE = r"[a-z][a-z0-9_]*"

TOPIC_RE = re.compile(rf"^fathom\.(?P<slug>{_SLUG_RE})\.(?P<aggregate>{_AGGREGATE_RE})\.v(?P<major>\d+)$")
EVENT_TYPE_RE = re.compile(rf"^fathom\.(?P<slug>{_SLUG_RE})\.(?P<aggregate>{_AGGREGATE_RE})\.(?P<verb>{_VERB_RE})$")

PROPOSAL_TOPIC_PATTERN = "fathom.{slug}.proposal.v{major}"


def topic_name(slug: AnySlug, aggregate: str, major: int) -> str:
    return f"fathom.{slug.value}.{aggregate}.v{major}"


def proposal_topic(slug: AnySlug, major: int = 1) -> str:
    return PROPOSAL_TOPIC_PATTERN.format(slug=slug.value, major=major)


def event_type(slug: AnySlug, aggregate: str, verb: str) -> str:
    return f"fathom.{slug.value}.{aggregate}.{verb}"
