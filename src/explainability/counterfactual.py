"""Counterfactual explanation module for CreditLens using DiCE.

Answers the applicant-facing question "what would need to change for this
loan to be approved?" by generating counterfactual feature vectors that
flip the model decision from default-risk to non-default
(ADR-007: SHAP + Counterfactual for regulatory explainability).
"""

from __future__ import annotations

from typing import Any

import dice_ml
import pandas as pd

from src.common.logging import configure_logging
from src.common.models import CounterfactualResult

configure_logging()


class CounterfactualGenerator:
    """DiCE-based counterfactual generator for credit decisions."""

    def __init__(
        self,
        model: Any,
        training_data: pd.DataFrame,
        continuous_features: list[str],
        outcome_name: str = "is_default",
        method: str = "random",
    ) -> None:
        """Initialize the counterfactual generator.

        Args:
            model: Trained sklearn-compatible classifier (predict_proba).
            training_data: Training DataFrame including the outcome column,
                used by DiCE to learn feature ranges.
            continuous_features: Names of continuous feature columns.
            outcome_name: Name of the binary outcome column.
            method: DiCE generation method ("random", "genetic", "kdtree").
        """
        self.outcome_name = outcome_name
        self.feature_columns = [col for col in training_data.columns if col != outcome_name]
        data = dice_ml.Data(
            dataframe=training_data,
            continuous_features=continuous_features,
            outcome_name=outcome_name,
        )
        wrapped_model = dice_ml.Model(model=model, backend="sklearn")
        self.dice = dice_ml.Dice(data, wrapped_model, method=method)

    def generate(
        self,
        X_single: pd.DataFrame,
        total_cfs: int = 3,
        desired_class: int = 0,
        features_to_vary: list[str] | None = None,
    ) -> pd.DataFrame | None:
        """Generate counterfactual feature vectors for one applicant.

        Args:
            X_single: Single-row DataFrame of the applicant's features
                (without the outcome column).
            total_cfs: Number of counterfactuals to request.
            desired_class: Target class for the counterfactuals
                (0 = non-default, i.e. approval).
            features_to_vary: Restrict changes to these features. Defaults
                to all features.

        Returns:
            DataFrame of counterfactual examples, or None if DiCE could
            not find any.
        """
        query = X_single[self.feature_columns].copy()
        explanation = self.dice.generate_counterfactuals(
            query,
            total_CFs=total_cfs,
            desired_class=desired_class,
            features_to_vary=features_to_vary if features_to_vary is not None else "all",
        )
        cf_examples = explanation.cf_examples_list[0].final_cfs_df
        if cf_examples is None or len(cf_examples) == 0:
            return None
        return cf_examples

    def explain(
        self,
        X_single: pd.DataFrame,
        total_cfs: int = 3,
        features_to_vary: list[str] | None = None,
    ) -> list[CounterfactualResult]:
        """Produce human-readable change recommendations for approval.

        Compares the closest counterfactual against the original feature
        values and reports each feature that must change.

        Args:
            X_single: Single-row DataFrame of the applicant's features.
            total_cfs: Number of counterfactuals to request from DiCE.
            features_to_vary: Restrict changes to these features.

        Returns:
            List of CounterfactualResult items (empty if no counterfactual
            was found).
        """
        cf_df = self.generate(X_single, total_cfs=total_cfs, features_to_vary=features_to_vary)
        if cf_df is None:
            return []
        original = X_single[self.feature_columns].iloc[0]
        best_cf = cf_df.iloc[0]
        return _diff_to_results(original, best_cf, self.feature_columns)


def _diff_to_results(
    original: pd.Series,
    counterfactual: pd.Series,
    feature_columns: list[str],
) -> list[CounterfactualResult]:
    """Convert a counterfactual row into per-feature change recommendations.

    Args:
        original: Original applicant feature values.
        counterfactual: Counterfactual feature values.
        feature_columns: Feature names to compare.

    Returns:
        List of CounterfactualResult for features whose values differ.
    """
    results: list[CounterfactualResult] = []
    for col in feature_columns:
        current = original[col]
        target = counterfactual[col]
        if _values_differ(current, target):
            results.append(
                CounterfactualResult(
                    parameter=col,
                    current_value=_format_value(current),
                    target_value=_format_value(target),
                )
            )
    return results


def _values_differ(current: Any, target: Any, rel_tol: float = 1e-6) -> bool:
    """Check whether two feature values are meaningfully different.

    Args:
        current: Original value.
        target: Counterfactual value.
        rel_tol: Relative tolerance for numeric comparison.

    Returns:
        True if the values differ beyond tolerance.
    """
    try:
        current_f = float(current)
        target_f = float(target)
    except (TypeError, ValueError):
        return str(current) != str(target)
    denom = max(abs(current_f), abs(target_f), 1.0)
    return abs(current_f - target_f) / denom > rel_tol


def _format_value(value: Any) -> str:
    """Format a feature value for display in an explanation.

    Args:
        value: Raw feature value.

    Returns:
        Human-readable string representation.
    """
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if value_f.is_integer():
        return str(int(value_f))
    return f"{value_f:.2f}"
