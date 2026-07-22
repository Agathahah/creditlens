"""Prediction endpoints for the CreditLens API.

POST /predict scores one applicant (default probability, risk tier,
approval recommendation); POST /survival predicts the time-to-default
survival curve (median survival time plus survival probabilities at
12/24/36 months). Target latency is <100ms per prediction; the measured
server-side latency is returned in every response for monitoring.
"""

from __future__ import annotations

import math
import time
import uuid

from fastapi import APIRouter, Depends

from src.api.schemas import ApplicantInput, PredictionResponse, SurvivalResponse
from src.api.state import ModelRegistry, get_registry

SURVIVAL_HORIZONS_MONTHS: list[int] = [12, 24, 36]

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


@router.post("/survival", response_model=SurvivalResponse)
def survival(
    payload: ApplicantInput, registry: ModelRegistry = Depends(get_registry)
) -> SurvivalResponse:
    """Predict the time-to-default survival curve for one applicant.

    Args:
        payload: Preprocessed applicant feature vector.
        registry: Application model registry.

    Returns:
        SurvivalResponse with the median survival time and survival
        probabilities at the 12/24/36-month horizons.
    """
    started = time.perf_counter()
    model = registry.require_survival_model()
    frame = registry.resolve_feature_frame(payload.applicant_id, payload.features)
    score_id = payload.applicant_id or f"score-{uuid.uuid4().hex[:12]}"

    survival_frame = frame[model.feature_cols] if model.feature_cols else frame
    median = float(model.predict_median_survival_time(survival_frame)[0])
    probs = model.survival_probability_at(
        survival_frame, [float(h) for h in SURVIVAL_HORIZONS_MONTHS]
    )

    latency_ms = (time.perf_counter() - started) * 1000.0
    return SurvivalResponse(
        score_id=score_id,
        median_survival_months=None if math.isinf(median) else median,
        survival_probabilities={
            horizon: float(probs.iloc[0][float(horizon)]) for horizon in SURVIVAL_HORIZONS_MONTHS
        },
        latency_ms=latency_ms,
    )
