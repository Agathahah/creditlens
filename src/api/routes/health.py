"""Health check endpoint for the CreditLens API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.schemas import HealthResponse
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
