"""Wire request/response models for `/model-bindings`. Document 22-pdm.md
§2.2, §5.6, §11.3 (line ~1363). `censoring_correction` is never a request
field -- `'ipcw_stabilized'` is the DB's only legal value (§2.2), so the
service sets it rather than trusting a caller to."""

from __future__ import annotations

import uuid

from fathom_schemas import FathomModel, NonEmptyStr, UtcDateTime


class CreateModelBindingRequest(FathomModel):
    tier: int
    equipment_family: NonEmptyStr
    taxonomy_version: NonEmptyStr
    registry_model_version: NonEmptyStr
    registry_model_uri: NonEmptyStr
    approval_ref: NonEmptyStr
    label_set_id: uuid.UUID


class ModelBindingResponse(FathomModel):
    binding_id: uuid.UUID
    tier: int
    equipment_family: str
    taxonomy_version: str
    registry_model_version: str
    registry_model_uri: str
    approval_ref: str
    label_set_id: uuid.UUID
    censoring_correction: str
    activated_at: UtcDateTime | None
    deactivated_at: UtcDateTime | None
