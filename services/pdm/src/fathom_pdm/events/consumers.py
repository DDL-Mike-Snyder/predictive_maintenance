"""Event consumer handlers. Document 22-pdm.md §8.1's invalidation triggers
table and 03 §4's inbox discipline (D2): "the `event_id` record and the
resulting state change commit together... Recording receipt before
processing is prohibited: a crash between the two permanently suppresses
the event" -- applied here specifically to `configuration.baseline_changed`,
which 03 §5.2 names as making that failure mode "silently prevent[]
prediction invalidation."

**Scope boundary, deliberately drawn here** (mirrors `services/criticality
.py`'s own boundary note): this module is the *business-logic* layer a
consumer loop calls once it has already deserialized an envelope and
payload off a real topic. It does NOT include a Kafka client, consumer
group/offset management, or schema-registry deserialization -- none of
that exists anywhere in this codebase yet (checked: no `confluent_kafka`
usage anywhere outside comments), and building it is shared
`packages/py-sync` infrastructure spanning every future service, not
PdM-specific "wire the consumers" work.

Of §8.1's six invalidation triggers, only two are externally-*evented*
(`configuration.baseline_changed`, `installed_item.removed`) and therefore
in scope for a "consumer" at all -- the other four (tier reassignment,
binding deactivation, calibration withdrawal, label set retraction) are
internal, triggered by PdM's own other subsystems (§3, §5.6, §6.5, and the
label-set retraction cascade respectively), none of which are built yet
either. Both handlers here are fully wired: real inbox row, real
`PredictionRepository.invalidate()` call (the SECURITY DEFINER function,
22-pdm.md §4.5) against every active prediction the event affects, all in
one transaction, exactly matching D2.

Local payload models below carry the same `[NOTE]` as `events/publishers
.py`'s `PredictionUpdated`: 03 §5.5 wants every event payload defined in
`packages/canonical-schemas`, but these actually belong to Registry's own
domain (Registry doesn't exist as code yet), so they're scoped locally to
this consumer for this vertical slice.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from fathom_schemas import EventEnvelope, FathomModel
from fathom_sync import Inbox

from fathom_pdm.repositories.prediction import PredictionRepository

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

_prediction_repo = PredictionRepository()
_inbox = Inbox()


class UnhandledEventTypeError(Exception):
    """Raised by `dispatch_event` for any of `catalog.CONSUMES`' ~17 other
    declared types that don't have a handler yet -- a future consumer loop
    should route this to a dead-letter/log path, not crash the process."""


class ConfigurationBaselineChanged(FathomModel):
    """[NOTE] see module docstring -- belongs in canonical-schemas/Registry's
    own domain eventually. 03 §6: baseline_id, baseline_epoch, the changed
    installed-item set, effective date."""

    baseline_id: uuid.UUID
    baseline_epoch: int
    changed_installed_item_ids: tuple[uuid.UUID, ...]
    effective_date: dt.datetime


class InstalledItemRemoved(FathomModel):
    """[NOTE] see module docstring. 03 §6: InstalledItemRef, removal date,
    disposition, failure indicator -- only `installed_item_id` is needed
    for invalidation itself; the rest is carried for completeness/future
    consumers of this same payload shape."""

    installed_item_id: uuid.UUID
    removal_date: dt.datetime
    disposition: str
    failure_indicator: bool


async def _invalidate_all_active(
    session: AsyncSession, *, installed_item_id: uuid.UUID, cause: str
) -> int:
    predictions = await _prediction_repo.get_all_active_for_item(
        session, installed_item_id=installed_item_id
    )
    invalidated = 0
    for prediction in predictions:
        if await _prediction_repo.invalidate(session, prediction.prediction_id, cause=cause):
            invalidated += 1
    return invalidated


async def handle_configuration_baseline_changed(
    session: AsyncSession, envelope: EventEnvelope, payload: ConfigurationBaselineChanged
) -> None:
    # 11 §3.2's mandatory comment template, copied verbatim: the event_id
    # record and the resulting state change commit together in the CALLER's
    # transaction (this function neither begins nor commits one); only a row
    # with `processed_at` set suppresses redelivery, so a crash between
    # `record` and `mark_processed` below re-delivers rather than silently
    # dropping this event -- the specific failure mode D2 exists to close,
    # named by 03 §5.2 as "silently prevent[ing] prediction invalidation"
    # for this exact event type.
    if await _inbox.already_applied(session, envelope.event_id):
        return
    await _inbox.record(session, envelope)

    for installed_item_id in payload.changed_installed_item_ids:
        await _invalidate_all_active(
            session, installed_item_id=installed_item_id, cause="baseline_changed"
        )

    await _inbox.mark_processed(session, envelope.event_id)


async def handle_installed_item_removed(
    session: AsyncSession, envelope: EventEnvelope, payload: InstalledItemRemoved
) -> None:
    # 11 §3.2's mandatory comment template, copied verbatim: see
    # handle_configuration_baseline_changed above for the full account --
    # applies identically here.
    if await _inbox.already_applied(session, envelope.event_id):
        return
    await _inbox.record(session, envelope)

    await _invalidate_all_active(
        session, installed_item_id=payload.installed_item_id, cause="item_removed"
    )

    await _inbox.mark_processed(session, envelope.event_id)


_HANDLERS: dict[str, Callable[[AsyncSession, EventEnvelope, FathomModel], Awaitable[None]]] = {
    "fathom.registry.configuration_baseline.changed": handle_configuration_baseline_changed,
    "fathom.registry.installed_item.removed": handle_installed_item_removed,
}

_PAYLOAD_TYPES: dict[str, type[FathomModel]] = {
    "fathom.registry.configuration_baseline.changed": ConfigurationBaselineChanged,
    "fathom.registry.installed_item.removed": InstalledItemRemoved,
}


async def dispatch_event(
    session: AsyncSession, envelope: EventEnvelope, raw_payload: dict[str, object]
) -> None:
    """The entry point a future Kafka consumer loop calls once it has
    deserialized one message's envelope and raw payload dict off a real
    topic. Raises `UnhandledEventTypeError` for any of `catalog.CONSUMES`'
    ~17 other declared types -- not a silent no-op, so a consumer loop
    can tell "nothing to do" apart from "this needs a handler built."
    """
    handler = _HANDLERS.get(envelope.event_type)
    if handler is None:
        raise UnhandledEventTypeError(envelope.event_type)
    payload_type = _PAYLOAD_TYPES[envelope.event_type]
    payload = payload_type.model_validate(raw_payload)
    await handler(session, envelope, payload)
