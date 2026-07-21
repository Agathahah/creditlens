"""CreditLens API application factory.

FastAPI app exposing credit scoring (POST /predict), explanation
(POST /explain), and health (GET /health) endpoints. Model artifacts are
loaded once at startup via the lifespan handler and shared through
``app.state.registry``; the service starts even when no artifact is
present so that /health can report readiness.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import explain, health, predict
from src.api.state import ModelRegistry
from src.common.logging import configure_logging
from src.explainability.shap_explainer import ShapExplainer
from src.ml.predict import CreditPredictor

configure_logging()

DEFAULT_MODEL_PATH = "models/xgboost_credit.joblib"


def build_feature_fetcher(
    repo_path: str | None,
) -> Callable[[str], dict[str, Any] | None] | None:
    """Build a Feast online-store fetcher when a repo path is configured.

    Args:
        repo_path: Feast repository directory (feature_store.yaml). When
            None or empty, online feature fetching is disabled.

    Returns:
        Callable mapping a loan/applicant id to its feature vector, or
        None when no feature store is configured.
    """
    if not repo_path:
        return None
    from src.feature_store.materialize import get_feature_store
    from src.feature_store.serve import fetch_feature_vector

    store = get_feature_store(repo_path)

    def fetch(loan_id: str) -> dict[str, Any] | None:
        return fetch_feature_vector(store, loan_id)

    return fetch


def load_registry(model_path: str | None = None) -> ModelRegistry:
    """Load ML artifacts from disk into a ModelRegistry.

    Args:
        model_path: Path to the model artifact. Defaults to the MODEL_PATH
            environment variable, falling back to models/xgboost_credit.joblib.

    Returns:
        Populated ModelRegistry, or an empty one if the artifact is absent.
    """
    path = model_path or os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    fetcher = build_feature_fetcher(os.environ.get("FEAST_REPO_PATH"))
    if not os.path.exists(path):
        return ModelRegistry(feature_fetcher=fetcher)

    predictor = CreditPredictor(model_path=path)
    explainer = ShapExplainer(predictor.model)
    feature_names = getattr(predictor.model, "feature_names_in_", None)
    expected = [str(name) for name in feature_names] if feature_names is not None else []
    return ModelRegistry(
        predictor=predictor,
        explainer=explainer,
        expected_features=expected,
        feature_fetcher=fetcher,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load model artifacts at startup and release them at shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None once startup is complete.
    """
    app.state.registry = load_registry()
    yield
    app.state.registry = ModelRegistry()


def create_app(registry: ModelRegistry | None = None) -> FastAPI:
    """Build the CreditLens FastAPI application.

    Args:
        registry: Pre-built ModelRegistry (used by tests). When None, the
            registry is loaded from disk during the lifespan startup.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="CreditLens API",
        description="Explainable credit scoring engine (XGBoost + SHAP + DiCE).",
        version="0.1.0",
        lifespan=lifespan if registry is None else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if registry is not None:
        app.state.registry = registry

    app.include_router(health.router)
    app.include_router(predict.router)
    app.include_router(explain.router)
    return app


app = create_app()
