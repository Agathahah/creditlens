"""Model registry holding the runtime ML artifacts for the API.

Keeps the trained predictor, SHAP explainer, and optional counterfactual
generator in one place so routes can depend on a single object and tests
can inject lightweight fakes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from fastapi import HTTPException, Request, status

from src.explainability.counterfactual import CounterfactualGenerator
from src.explainability.shap_explainer import ShapExplainer
from src.ml.predict import CreditPredictor
from src.ml.survival import SurvivalAnalysis


@dataclass
class ModelRegistry:
    """Container for the ML artifacts served by the API."""

    predictor: CreditPredictor | None = None
    explainer: ShapExplainer | None = None
    counterfactual_generator: CounterfactualGenerator | None = None
    expected_features: list[str] = field(default_factory=list)
    feature_fetcher: Callable[[str], dict[str, Any] | None] | None = None
    survival_model: SurvivalAnalysis | None = None

    @property
    def model_loaded(self) -> bool:
        """Whether a scoring model is available."""
        return self.predictor is not None and self.predictor.model is not None

    def require_predictor(self) -> CreditPredictor:
        """Return the predictor or fail with 503 when no model is loaded.

        Returns:
            The loaded CreditPredictor.

        Raises:
            HTTPException: 503 if no model is loaded.
        """
        if self.predictor is None or self.predictor.model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No scoring model is loaded.",
            )
        return self.predictor

    def require_survival_model(self) -> SurvivalAnalysis:
        """Return the survival model or fail with 503 when unavailable.

        Returns:
            The loaded SurvivalAnalysis model.

        Raises:
            HTTPException: 503 if no survival model is loaded.
        """
        if self.survival_model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No survival model is loaded.",
            )
        return self.survival_model

    def require_explainer(self) -> ShapExplainer:
        """Return the SHAP explainer or fail with 503 when unavailable.

        Returns:
            The loaded ShapExplainer.

        Raises:
            HTTPException: 503 if no explainer is loaded.
        """
        if self.explainer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No SHAP explainer is loaded.",
            )
        return self.explainer

    def build_feature_frame(self, features: dict[str, float]) -> pd.DataFrame:
        """Build a single-row feature DataFrame in the model's column order.

        Args:
            features: Mapping of feature name to preprocessed numeric value.

        Returns:
            Single-row DataFrame with columns ordered as the model expects.

        Raises:
            HTTPException: 422 if required model features are missing.
        """
        expected = self.expected_features or sorted(features)
        missing = [name for name in expected if name not in features]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required features: {missing}",
            )
        return pd.DataFrame([{name: features[name] for name in expected}])

    def resolve_feature_frame(
        self, applicant_id: str | None, features: dict[str, float] | None
    ) -> pd.DataFrame:
        """Resolve the feature frame from the payload or the online store.

        Inline features take precedence; otherwise the Feast online store
        is queried by applicant_id (ADR-006).

        Args:
            applicant_id: Loan/applicant entity key for online lookup.
            features: Inline preprocessed feature values, if provided.

        Returns:
            Single-row feature DataFrame ready for scoring.

        Raises:
            HTTPException: 422 when neither inline features nor an online
                lookup are possible; 404 when the entity is not in the
                online store.
        """
        if features:
            return self.build_feature_frame(features)
        if self.feature_fetcher is None or not applicant_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide 'features', or 'applicant_id' with a configured feature store.",
            )
        fetched = self.feature_fetcher(applicant_id)
        if fetched is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No online features found for applicant '{applicant_id}'.",
            )
        return self.build_feature_frame(fetched)


def get_registry(request: Request) -> ModelRegistry:
    """FastAPI dependency returning the app's ModelRegistry.

    Args:
        request: Incoming request bound to the FastAPI app.

    Returns:
        The application-wide ModelRegistry.
    """
    registry: ModelRegistry = request.app.state.registry
    return registry
