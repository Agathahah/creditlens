"""Pydantic request/response schemas for the CreditLens API.

Defines the public contract of the prediction and explanation endpoints.
All responses are JSON-serializable and include service latency so the
<100ms prediction target can be monitored per request.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.common.models import CounterfactualResult, RiskTier


class ApplicantInput(BaseModel):
    """Preprocessed applicant feature vector for scoring.

    Feature keys must match the columns the deployed model was trained on
    (see ``src.features.features``); values are the already-encoded
    numeric representations produced by ``preprocess_features``.
    """

    applicant_id: str | None = Field(
        default=None,
        description="Applicant/loan identifier; used as the Feast entity key "
        "when 'features' is omitted",
        examples=["app-001"],
    )
    features: dict[str, float] | None = Field(
        default=None,
        min_length=1,
        description="Mapping of model feature name to preprocessed numeric value. "
        "Omit to fetch features from the Feast online store by applicant_id.",
        examples=[{"loan_amnt": 15000.0, "int_rate": 13.5, "dti_eff": 18.2}],
    )


class PredictionResponse(BaseModel):
    """Credit scoring decision for one applicant."""

    score_id: str = Field(..., description="Unique transaction ID for this evaluation")
    risk_score: float = Field(..., ge=0, le=1, description="Predicted probability of default")
    risk_tier: RiskTier = Field(..., description="Assigned risk tier (low, medium, high)")
    approved: bool = Field(..., description="Automated approval recommendation")
    latency_ms: float = Field(..., ge=0, description="Server-side processing time in ms")


class FeatureContribution(BaseModel):
    """A single feature's SHAP contribution to one prediction."""

    feature: str = Field(..., description="Feature name")
    shap_value: float = Field(..., description="SHAP contribution to the default probability")
    direction: str = Field(..., description="Either 'increases_risk' or 'decreases_risk'")


class ExplanationResponse(BaseModel):
    """SHAP + counterfactual explanation for one prediction (ADR-007)."""

    score_id: str = Field(..., description="Unique transaction ID for this evaluation")
    risk_score: float = Field(..., ge=0, le=1, description="Predicted probability of default")
    base_value: float = Field(..., description="Model expected value (SHAP base value)")
    top_features: list[FeatureContribution] = Field(
        default_factory=list, description="Top contributing features, largest |SHAP| first"
    )
    counterfactuals: list[CounterfactualResult] = Field(
        default_factory=list,
        description="Feature changes that would flip the decision toward approval",
    )
    latency_ms: float = Field(..., ge=0, description="Server-side processing time in ms")


class HealthResponse(BaseModel):
    """Service health and model readiness."""

    status: str = Field(..., description="Service status ('ok')")
    model_loaded: bool = Field(..., description="Whether a scoring model is loaded")
    explainer_loaded: bool = Field(..., description="Whether a SHAP explainer is loaded")
