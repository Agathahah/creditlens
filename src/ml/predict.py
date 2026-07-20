"""Inference and scoring module for CreditLens credit engine.

Loads trained models, predicts default probabilities, maps risk tiers,
and provides automated credit decision recommendations.
"""

from typing import Any

import numpy as np
import pandas as pd

from src.common.models import RiskTier, ScoreResult
from src.ml.train import load_model_artifact


class CreditPredictor:
    """Predictor service for evaluating applicant default probabilities and risk tiers."""

    def __init__(
        self,
        model: Any | None = None,
        model_path: str | None = None,
        approval_threshold: float = 0.20,
    ) -> None:
        """Initialize CreditPredictor.

        Args:
            model: Pre-loaded model object.
            model_path: Path to model artifact on disk if model is None.
            approval_threshold: Probability threshold below which loans are
                recommended for approval.
        """
        if model is not None:
            self.model = model
        elif model_path is not None:
            self.model = load_model_artifact(model_path)
        else:
            self.model = None

        self.approval_threshold = approval_threshold

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict default probabilities for input feature DataFrame.

        Args:
            X: Preprocessed feature DataFrame.

        Returns:
            Array of default probabilities.
        """
        if self.model is None:
            raise ValueError("No model loaded for prediction.")

        # Handle 1D or 2D probability outputs
        proba = self.model.predict_proba(X)
        if proba.ndim == 2 and proba.shape[1] >= 2:
            return np.asarray(proba[:, 1], dtype=float)
        return np.asarray(proba, dtype=float)

    def classify_risk_tier(self, probability: float) -> RiskTier:
        """Categorize default probability into risk tier.

        Args:
            probability: Default probability score (0.0 to 1.0).

        Returns:
            RiskTier enum (LOW, MEDIUM, HIGH).
        """
        if probability < 0.10:
            return RiskTier.LOW
        elif probability < 0.25:
            return RiskTier.MEDIUM
        else:
            return RiskTier.HIGH

    def score_applicant(self, X_single: pd.DataFrame, score_id: str = "eval-001") -> ScoreResult:
        """Evaluate a single applicant feature row and return ScoreResult.

        Args:
            X_single: Single row DataFrame containing applicant features.
            score_id: Unique evaluation transaction ID.

        Returns:
            ScoreResult object.
        """
        prob_arr = self.predict_proba(X_single)
        prob = float(prob_arr[0])
        tier = self.classify_risk_tier(prob)
        approved = prob < self.approval_threshold

        return ScoreResult(
            score_id=score_id,
            risk_score=prob,
            risk_tier=tier,
            approved=approved,
        )
