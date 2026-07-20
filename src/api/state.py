"""Model registry holding the runtime ML artifacts for the API.

Keeps the trained predictor, SHAP explainer, and optional counterfactual
generator in one place so routes can depend on a single object and tests
can inject lightweight fakes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from fastapi import HTTPException, Request, status

from src.explainability.counterfactual import CounterfactualGenerator
from src.explainability.shap_explainer import ShapExplainer
from src.ml.predict import CreditPredictor


@dataclass
class ModelRegistry:
    """Container for the ML artifacts served by the API."""

    predictor: CreditPredictor | None = None
    explainer: ShapExplainer | None = None
    counterfactual_generator: CounterfactualGenerator | None = None
    expected_features: list[str] = field(default_factory=list)

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


def get_registry(request: Request) -> ModelRegistry:
    """FastAPI dependency returning the app's ModelRegistry.

    Args:
        request: Incoming request bound to the FastAPI app.

    Returns:
        The application-wide ModelRegistry.
    """
    registry: ModelRegistry = request.app.state.registry
    return registry
