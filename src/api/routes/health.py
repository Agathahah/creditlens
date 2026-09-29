"""Health check endpoint for the CreditLens API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from src.api.schemas import HealthResponse, ReadinessResponse
from src.api.state import ModelRegistry, get_registry

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(registry: ModelRegistry = Depends(get_registry)) -> HealthResponse:
    """Report service health and model readiness.

    Args:
        registry: Application model registry.

    Returns:
        HealthResponse with service and artifact status.
    """
    return HealthResponse(
        status="ok",
        model_loaded=registry.model_loaded,
        explainer_loaded=registry.explainer is not None,
    )


@router.get("/live")
def live() -> dict[str, str]:
    """Report process liveness without checking model availability.

    Returns:
        A process-level status response.
    """
    return {"status": "alive"}


@router.get("/ready", response_model=ReadinessResponse)
def ready(response: Response, registry: ModelRegistry = Depends(get_registry)) -> ReadinessResponse:
    """Report scoring readiness and reject unverified or missing bundles.

    Args:
        response: HTTP response whose status is set to 503 when unavailable.
        registry: Application model registry.

    Returns:
        Bundle status. Model quality and deployment approval are separate gates.
    """
    if not registry.scoring_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if registry.scoring_ready else "not_ready",
        model_loaded=registry.model_loaded,
        bundle_verified=registry.bundle_verified,
    )
