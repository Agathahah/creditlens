"""Explanation endpoint for the CreditLens API (ADR-007).

POST /explain returns the SHAP local explanation for one prediction and,
when a counterfactual generator is configured, actionable feature changes
that would flip the decision toward approval.
"""

from __future__ import annotations

import time
import uuid

import pandas as pd
from fastapi import APIRouter, Depends

from src.api.schemas import ApplicantInput, ExplanationResponse, FeatureContribution
from src.api.state import ModelRegistry, get_registry
from src.common.models import CounterfactualResult

router = APIRouter(tags=["explainability"])


def _generate_counterfactuals(
    registry: ModelRegistry, frame: pd.DataFrame, total_cfs: int
) -> list[CounterfactualResult]:
    """Generate counterfactuals when a generator is configured.

    Args:
        registry: Application model registry.
        frame: Single-row feature DataFrame.
        total_cfs: Number of counterfactuals to request.

    Returns:
        Counterfactual recommendations, or an empty list if unavailable.
    """
    generator = registry.counterfactual_generator
    if generator is None:
        return []
    return generator.explain(frame, total_cfs=total_cfs)


@router.post("/explain", response_model=ExplanationResponse)
def explain(
    payload: ApplicantInput,
    top_n: int = 5,
    total_cfs: int = 2,
    registry: ModelRegistry = Depends(get_registry),
) -> ExplanationResponse:
    """Explain the credit decision for a single applicant.

    Args:
        payload: Preprocessed applicant feature vector.
        top_n: Number of top SHAP features to include.
        total_cfs: Number of counterfactuals to request (if configured).
        registry: Application model registry.

    Returns:
        ExplanationResponse with SHAP attributions and counterfactuals.
    """
    started = time.perf_counter()
    predictor = registry.require_predictor()
    explainer = registry.require_explainer()
    frame = registry.build_feature_frame(payload.features)
    score_id = payload.applicant_id or f"score-{uuid.uuid4().hex[:12]}"

    risk_score = float(predictor.predict_proba(frame)[0])
    explanation = explainer.explain_single(frame, top_n=top_n)
    counterfactuals = _generate_counterfactuals(registry, frame, total_cfs)

    latency_ms = (time.perf_counter() - started) * 1000.0
    return ExplanationResponse(
        score_id=score_id,
        risk_score=risk_score,
        base_value=explanation["base_value"],
        top_features=[FeatureContribution(**item) for item in explanation["top_features"]],
        counterfactuals=counterfactuals,
        latency_ms=latency_ms,
    )
