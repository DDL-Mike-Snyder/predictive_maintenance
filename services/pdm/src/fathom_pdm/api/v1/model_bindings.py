"""`/api/v1/pdm/model-bindings*`. Document 22-pdm.md §11.3 (line ~1363):
both operations are `internal` substitution, `state-changing`, not
agent-eligible. HTTP shape only -- never touches a session directly beyond
what `deps.py` hands it, never emits SQL (09 §4.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import ProblemException
from fathom_schemas import ClassificationLabel, ClassificationLevel
from fathom_sync import OutboxWriter, UnitOfWork

from fathom_pdm.deps import Principal, current_principal, get_outbox_writer, get_uow
from fathom_pdm.models import ModelBinding
from fathom_pdm.repositories.model_binding import ModelBindingRepository
from fathom_pdm.repositories.prediction import PredictionRepository
from fathom_pdm.schemas.model_binding import CreateModelBindingRequest, ModelBindingResponse
from fathom_pdm.services import model_binding as model_binding_service

router = APIRouter()

_binding_repo = ModelBindingRepository()
_prediction_repo = PredictionRepository()


def _to_response(binding: ModelBinding) -> ModelBindingResponse:
    return ModelBindingResponse(
        binding_id=binding.binding_id,
        tier=binding.tier,
        equipment_family=binding.equipment_family,
        taxonomy_version=binding.taxonomy_version,
        registry_model_version=binding.registry_model_version,
        registry_model_uri=binding.registry_model_uri,
        approval_ref=binding.approval_ref,
        label_set_id=binding.label_set_id,
        censoring_correction=binding.censoring_correction,
        activated_at=binding.activated_at,
        deactivated_at=binding.deactivated_at,
    )


_REFUSAL_STATUS_TITLE = {
    "unaccepted_propensity_model": "Propensity model not accepted",
    "unpowered_label_set_family": "Label set's family is not powered",
    "no_calibration_record": "No calibration record for this triple",
}


@router.post(
    "/model-bindings",
    response_model=ModelBindingResponse,
    status_code=201,
    openapi_extra=operation_extra(
        operation_id="pdm_create_model_binding",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.STATE_CHANGING,
        summary=(
            "Register a Domino registry model version against a "
            "(tier, equipment_family, taxonomy_version) triple. Draft, not yet activated."
        ),
        aggregate="model_binding",
    ),
)
async def create_model_binding(
    body: CreateModelBindingRequest,
    _principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> ModelBindingResponse:
    binding = await model_binding_service.create_binding(
        uow,
        _binding_repo,
        tier=body.tier,
        equipment_family=body.equipment_family,
        taxonomy_version=body.taxonomy_version,
        registry_model_version=body.registry_model_version,
        registry_model_uri=body.registry_model_uri,
        approval_ref=body.approval_ref,
        label_set_id=body.label_set_id,
    )
    return _to_response(binding)


@router.post(
    "/model-bindings/{binding_id}/activate",
    response_model=ModelBindingResponse,
    status_code=200,
    openapi_extra=operation_extra(
        operation_id="pdm_activate_model_binding",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.STATE_CHANGING,
        summary=(
            "Activate a model binding. Refuses on unaccepted propensity model, unpowered "
            "label set, or absent calibration record (§5.6)."
        ),
        aggregate="model_binding",
    ),
)
async def activate_model_binding(
    binding_id: uuid.UUID,
    _principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    outbox: OutboxWriter = Depends(get_outbox_writer),
) -> ModelBindingResponse:
    # [PLACEHOLDER] real classification derives from the union of the
    # affected family's own installed items' classification (03 §7.3);
    # matches services/scoring.py's own placeholder for this vertical slice.
    classification = ClassificationLabel(level=ClassificationLevel.U)

    try:
        binding = await model_binding_service.activate_binding(
            uow,
            outbox,
            _binding_repo,
            _prediction_repo,
            binding_id=binding_id,
            classification=classification,
        )
    except model_binding_service.BindingNotFoundError as exc:
        raise ProblemException(
            type="urn:fathom:problem:pdm:model-binding-not-found",
            title="Model binding not found",
            status=404,
        ) from exc
    except model_binding_service.BindingAlreadyActivatedError as exc:
        raise ProblemException(
            type="urn:fathom:problem:pdm:model-binding-already-activated",
            title="Model binding already activated",
            status=409,
        ) from exc
    except model_binding_service.BindingRefusedError as exc:
        raise ProblemException(
            type=f"urn:fathom:problem:pdm:model-binding-refused:{exc.reason}",
            title=_REFUSAL_STATUS_TITLE[exc.reason],
            status=409,
            detail=str(exc),
        ) from exc

    return _to_response(binding)
