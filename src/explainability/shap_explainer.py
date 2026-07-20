"""SHAP explainability module for CreditLens credit scoring engine.

Provides global explainability (feature importance ranking across a dataset)
and local explainability (per-prediction feature attributions) using SHAP,
with JSON-serializable outputs for API responses and database persistence
(ADR-007: SHAP + Counterfactual for regulatory explainability).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import shap

from src.common.logging import configure_logging

configure_logging()


class ShapExplainer:
    """SHAP-based explainer wrapping a trained credit scoring model."""

    def __init__(
        self,
        model: Any,
        background_data: pd.DataFrame | None = None,
        feature_names: list[str] | None = None,
    ) -> None:
        """Initialize ShapExplainer with a trained model.

        Args:
            model: Trained XGBoost / LightGBM / Logistic Regression model.
            background_data: Reference dataset for non-tree explainers.
                Required for linear models, optional for tree ensembles.
            feature_names: Ordered feature names. Inferred from input
                DataFrames when omitted.
        """
        self.model = model
        self.feature_names = feature_names
        self.explainer = self._build_explainer(model, background_data)

    @staticmethod
    def _build_explainer(model: Any, background_data: pd.DataFrame | None) -> Any:
        """Select the appropriate SHAP explainer for the model type.

        Args:
            model: Trained model object.
            background_data: Reference dataset for non-tree explainers.

        Returns:
            Configured shap explainer instance.

        Raises:
            ValueError: If a non-tree model is given without background data.
        """
        model_module = type(model).__module__
        if model_module.startswith(("xgboost", "lightgbm")):
            return shap.TreeExplainer(model)
        if background_data is None:
            raise ValueError("background_data is required for non-tree models.")
        return shap.LinearExplainer(model, background_data)

    def shap_values(self, X: pd.DataFrame) -> np.ndarray:
        """Compute SHAP values for a feature matrix.

        Args:
            X: Preprocessed feature DataFrame.

        Returns:
            2D array of SHAP values with shape (n_samples, n_features),
            attributed to the positive (default) class.
        """
        values = self.explainer.shap_values(X)
        if isinstance(values, list):
            # Multi-class output: take positive class contributions
            values = values[-1]
        arr = np.asarray(values, dtype=float)
        if arr.ndim == 3:
            arr = arr[:, :, -1]
        return arr

    def _resolve_feature_names(self, X: pd.DataFrame) -> list[str]:
        """Resolve feature names from configuration or the input DataFrame.

        Args:
            X: Feature DataFrame.

        Returns:
            Ordered list of feature names.
        """
        if self.feature_names is not None:
            return self.feature_names
        return [str(col) for col in X.columns]

    def global_feature_importance(self, X: pd.DataFrame) -> dict[str, float]:
        """Rank features by global importance (mean absolute SHAP value).

        Args:
            X: Preprocessed feature DataFrame representing the population.

        Returns:
            Mapping of feature name to mean |SHAP| value, sorted descending.
        """
        values = self.shap_values(X)
        importances = np.abs(values).mean(axis=0)
        names = self._resolve_feature_names(X)
        ranked = sorted(zip(names, importances), key=lambda item: item[1], reverse=True)
        return {name: float(score) for name, score in ranked}

    def explain_single(self, X_single: pd.DataFrame, top_n: int = 10) -> dict[str, Any]:
        """Generate a local explanation for a single prediction.

        Args:
            X_single: Single-row feature DataFrame for one applicant.
            top_n: Number of top contributing features to include.

        Returns:
            JSON-serializable dict with base value, per-feature SHAP
            contributions, and the top contributing features.
        """
        if len(X_single) != 1:
            raise ValueError("explain_single expects exactly one row.")
        values = self.shap_values(X_single)[0]
        names = self._resolve_feature_names(X_single)
        contributions = {name: float(val) for name, val in zip(names, values)}
        top = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)[:top_n]
        return {
            "base_value": self._base_value(),
            "shap_contributions": contributions,
            "top_features": [
                {
                    "feature": name,
                    "shap_value": val,
                    "direction": "increases_risk" if val > 0 else "decreases_risk",
                }
                for name, val in top
            ],
        }

    def _base_value(self) -> float:
        """Return the explainer's expected (base) value for the positive class.

        Returns:
            Scalar base value.
        """
        expected = self.explainer.expected_value
        if isinstance(expected, (list, np.ndarray)):
            expected_arr = np.asarray(expected, dtype=float).ravel()
            return float(expected_arr[-1])
        return float(expected)


def build_shap_records(
    loan_ids: list[str],
    shap_values: np.ndarray,
    feature_names: list[str],
    model_name: str,
) -> list[dict[str, Any]]:
    """Serialize SHAP values into rows for database persistence and monitoring.

    Args:
        loan_ids: Loan identifiers aligned with shap_values rows.
        shap_values: 2D array of SHAP values (n_samples, n_features).
        feature_names: Ordered feature names matching columns.
        model_name: Identifier of the model that produced the values.

    Returns:
        List of dicts, one per loan, ready for bulk insert.
    """
    if len(loan_ids) != shap_values.shape[0]:
        raise ValueError("loan_ids length must match shap_values rows.")
    created_at = datetime.now(UTC).isoformat()
    return [
        {
            "loan_id": loan_id,
            "model_name": model_name,
            "shap_values": {name: float(val) for name, val in zip(feature_names, row)},
            "created_at": created_at,
        }
        for loan_id, row in zip(loan_ids, shap_values)
    ]
