"""Request boundary checks using synthetic fixtures; not real model acceptance."""

from __future__ import annotations

import math

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.state import ModelRegistry


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999", '"10"', "true"])
def test_invalid_numeric_payload_is_safe_422(token: str) -> None:
    """Non-finite and coerced numeric input must not reach scoring or cause HTTP 500."""
    client = TestClient(create_app(ModelRegistry()))
    response = client.post(
        "/predict",
        content='{"features":{"annual_inc":' + token + "}}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert all("input" not in item and "ctx" not in item for item in response.json()["detail"])


def test_unknown_fields_and_excessive_features_are_rejected() -> None:
    """Request contract rejects unrecognized envelopes and unbounded feature dictionaries."""
    client = TestClient(create_app(ModelRegistry()))
    for payload in (
        {"features": {"annual_inc": 100.0}, "secret": "private-value"},
        {"features": {f"feature_{i}": 1.0 for i in range(129)}},
        {"features": {"annual_inc": 1.0}, "applicant_id": "x" * 129},
    ):
        response = client.post("/predict", json=payload)
        assert response.status_code == 422
        assert "private-value" not in response.text


def test_inline_and_fetched_schema_cannot_silently_drop_features() -> None:
    """The same numeric/schema checks protect inline and online-store feature frames."""
    registry = ModelRegistry(expected_features=["annual_inc"])
    for values in (
        {"annual_inc": 10.0, "future_outcome": 1.0},
        {"annual_inc": math.inf},
    ):
        with pytest.raises(HTTPException) as error:
            registry.build_feature_frame(values)
        assert error.value.status_code == 422
        registry.feature_fetcher = lambda _: values
        with pytest.raises(HTTPException) as fetched_error:
            registry.resolve_feature_frame("fixture", None)
        assert fetched_error.value.status_code == 422


def test_cors_is_closed_by_default_and_explicit_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser origin is allowed only when explicitly configured; this is not authentication."""
    monkeypatch.delenv("API_ALLOWED_ORIGINS", raising=False)
    headers = {"Origin": "https://demo.example", "Access-Control-Request-Method": "POST"}
    response = TestClient(create_app(ModelRegistry())).options("/predict", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    monkeypatch.setenv("API_ALLOWED_ORIGINS", "https://demo.example")
    client = TestClient(create_app(ModelRegistry()))
    assert (
        client.options("/predict", headers=headers).headers["access-control-allow-origin"]
        == headers["Origin"]
    )
    headers["Origin"] = "https://other.example"
    assert client.options("/predict", headers=headers).status_code == 400
    assert client.get("/live").status_code == 200
    assert client.get("/ready").status_code == 503


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example",
        "https://demo.example/path",
        "https://user:pass@demo.example",
        "https://demo.example:99999",
    ],
)
def test_invalid_cors_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    """Misconfiguration cannot silently expand browser access."""
    monkeypatch.setenv("API_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError):
        create_app(ModelRegistry())
