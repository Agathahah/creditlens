"""Prediction endpoint for the CreditLens API.

POST /predict scores one applicant and returns the default probability,
risk tier, and automated approval recommendation. Target latency is
<100ms per prediction; the measured server-side latency is returned in
every response for monitoring.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends

from src.api.schemas import ApplicantInput, PredictionResponse
from src.api.state import ModelRegistry, get_registry

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictionResponse)
def predict(
    payload: ApplicantInput, registry: ModelRegistry = Depends(get_registry)
) -> PredictionResponse:
    """Score a single applicant.

    Args:
        payload: Preprocessed applicant feature vector.
        registry: Application model registry.

    Returns:
        PredictionResponse with risk score, tier, decision, and latency.
    """
    started = time.perf_counter()
    predictor = registry.require_predictor()
    frame = registry.resolve_feature_frame(payload.applicant_id, payload.features)
    score_id = payload.applicant_id or f"score-{uuid.uuid4().hex[:12]}"

    result = predictor.score_applicant(frame, score_id=score_id)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return PredictionResponse(
        score_id=result.score_id,
        risk_score=result.risk_score,
        risk_tier=result.risk_tier,
        approved=result.approved,
        latency_ms=latency_ms,
    )
