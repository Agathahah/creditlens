"""Authenticated loopback-only research API; accepted mortgage evidence is not fintech readiness."""

from __future__ import annotations

import argparse
import hmac
import math
import sqlite3
import ssl
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
import sklearn
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from threadpoolctl import threadpool_limits

from src.research.freddie_history_test import EXECUTION_SHA
from src.research.freddie_history_train import PROTOCOL_SHA
from src.research.freddie_metrics import validation_gates
from src.research.freddie_monitoring import AuditStore, private_file
from src.research.freddie_preflight import read_object, sha256
from src.research.freddie_release import assess_validation_candidate

RESEARCH_SCOPE = "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
MAX_BODY_BYTES = 8192
RATE_PER_MINUTE = 60


class FeatureRequest(BaseModel):
    """Exact named domain feature vector; no loan/customer IDs, tiers or credit decisions."""

    model_config = ConfigDict(extra="forbid", strict=True)
    features: dict[str, float | int | None] = Field(min_length=19, max_length=19)

    @field_validator("features")
    @classmethod
    def validate_finite(
        cls, values: dict[str, float | int | None]
    ) -> dict[str, float | int | None]:
        """Reject booleans and non-finite numbers before model input conversion.

        Args:
            values: Named numeric feature vector; NULL means the locked missing rule.

        Returns:
            Validated raw values.
        """
        if any(
            isinstance(v, bool) or (v is not None and not math.isfinite(v)) for v in values.values()
        ):
            raise ValueError("Only finite numeric feature values or null are allowed")
        return values


def verify_bundle(path: Path) -> tuple[dict[str, Any], Any]:
    """Recompute both research gates and check artifact/version identity before loading weights.

    Args:
        path: Trusted locally created private research bundle manifest.

    Returns:
        Verified research manifest and own loaded candidate; never production authorization.

    Raises:
        ValueError: Scope, gate, artifact, schema or runtime mismatches.
    """
    bundle = read_object(path)
    if (
        bundle["scope"] != RESEARCH_SCOPE
        or bundle["public_scoring_authorized"] is not False
        or bundle["production_scoring_release"] != "HOLD"
        or bundle["protocol_sha256"] != PROTOCOL_SHA
    ):
        raise ValueError("Private research scope only")
    protocol, run, test = (Path(bundle[k]) for k in ("protocol_path", "validation_run", "test_run"))
    config = read_object(protocol)
    report = read_object(test / "test_report.json")
    execution = read_object(Path(bundle["execution_path"]))
    validation = read_object(run / "validation_report.json")
    if (
        sha256(protocol) != PROTOCOL_SHA
        or bundle["features"] != config["features"]
        or sha256(Path(bundle["execution_path"])) != EXECUTION_SHA
        or report["execution_sha256"] != EXECUTION_SHA
        or report["test_source_sha256"] != execution["test_source_sha256"]
        or execution["candidate_sha256"] != bundle["candidate_sha256"]
        or report["frozen_test_opened"] is not True
        or bundle["feature_dtype"] != "float32"
        or report["test_decision"] != "PASS_RESEARCH_TEST"
        or report["scope"] != RESEARCH_SCOPE
        or report["test_vintage_consumed"] != 2022
        or bundle["validation_report_sha256"] != sha256(run / "validation_report.json")
        or bundle["test_report_sha256"] != sha256(test / "test_report.json")
        or bundle["candidate_sha256"] != sha256(run / "candidate_pipeline.joblib")
        or report["candidate_sha256"] != bundle["candidate_sha256"]
        or validation["candidate_sha256"] != bundle["candidate_sha256"]
        or not assess_validation_candidate(run, protocol)["eligible_for_test_consideration"]
    ):
        raise ValueError("Research evidence/artifact identity mismatch")
    gates = dict(config["proposed_research_gates"])
    gates["minimum_unique_adverse_loans"] = {
        "validation": gates["minimum_unique_adverse_loans"]["frozen_test"]
    }
    recomputed = validation_gates(
        report["metrics"], report["uncertainty"], report["counts"]["unique_adverse_loans"], gates
    )
    if recomputed != report["test_gates"] or not all(recomputed.values()):
        raise ValueError("Independent research test gate failed")
    if bundle["sklearn"] != sklearn.__version__ or bundle["numpy"] != np.__version__:
        raise ValueError("Research runtime mismatch")
    model = joblib.load(
        run / "candidate_pipeline.joblib"
    )  # Own artifact bound to both real evaluations.
    if list(model.feature_names_in_) != bundle["features"]:
        raise ValueError("Loaded model feature order mismatch")
    return bundle, model


def create_app(bundle_path: Path, token: str, audit_db: Path | None = None) -> FastAPI:
    """Create a bounded research app; the executable binds only to loopback.

    Args:
        bundle_path: Accepted private research bundle.
        token: Owner-only random bearer credential, at least32characters.
        audit_db: Optional bounded private SQLite journal outside Git.

    Returns:
        Authenticated app with explicit research and production statuses.

    Raises:
        ValueError: Missing credential or invalid research bundle.
    """
    if len(token) < 32:
        raise ValueError("A private random bearer token of at least32characters is required")
    bundle, model = verify_bundle(bundle_path)
    journal = AuditStore(audit_db) if audit_db is not None else None
    app = FastAPI(
        title="CreditLens private mortgage research",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    calls: deque[float] = deque()
    counter_lock, model_lock = Lock(), Lock()

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Reject malformed input without echoing feature values or non-JSON NaN tokens."""
        return JSONResponse({"detail": "Invalid research feature request"}, status_code=422)

    async def dispatch(request: Request, call_next: Any) -> Any:
        authorization = request.headers.get("authorization", "")
        if not hmac.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        now = monotonic()
        with counter_lock:
            while calls and calls[0] <= now - 60:
                calls.popleft()
            if len(calls) >= RATE_PER_MINUTE:
                return JSONResponse({"detail": "Research request rate exceeded"}, status_code=429)
            calls.append(now)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                return JSONResponse({"detail": "Request body too large"}, status_code=413)
            body.extend(chunk)
        request._body = bytes(body)
        return await call_next(request)

    @app.middleware("http")
    async def boundary(request: Request, call_next: Any) -> Any:
        request.state.request_id = str(uuid4())
        request.state.audit_probability = None
        started_at, started = datetime.now(UTC), monotonic()
        try:
            response = await dispatch(request, call_next)
        except Exception:
            # Keep model/input exceptions out of responses and private audit payloads.
            request.state.audit_probability = None
            response = JSONResponse({"detail": "Research request unavailable"}, status_code=503)
        if journal is not None:
            route = request.url.path if request.url.path in ("/score", "/ready") else "/other"
            method = request.method if request.method in ("GET", "POST") else "OTHER"
            try:
                journal.record(
                    request.state.request_id,
                    started_at,
                    method,
                    route,
                    response.status_code,
                    (monotonic() - started) * 1000,
                    bundle["model_id"],
                    bundle["candidate_sha256"],
                    request.state.audit_probability,
                )
            except (ValueError, OSError, sqlite3.Error):
                response = JSONResponse({"detail": "Research audit unavailable"}, status_code=503)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/ready")
    def ready() -> dict[str, Any]:
        """Report private research readiness separately from production scoring."""
        return {
            "research_ready": True,
            "audit_enabled": journal is not None,
            "production_scoring_release": "HOLD",
            "scope": RESEARCH_SCOPE,
            "model_id": bundle["model_id"],
            "public_scoring_authorized": False,
            "point_in_time_verified": False,
        }

    @app.post("/score")
    def score(payload: FeatureRequest, request: Request) -> dict[str, Any]:
        """Predict one exact ordered feature vector with the already-fitted pipeline."""
        if set(payload.features) != set(bundle["features"]):
            raise HTTPException(status_code=422, detail="Exact feature schema required")
        ranges = {
            "upb": (0.000001, 1e10),
            "loan_age": (0, 600),
            "remaining_months": (0, 600),
            "interest_rate": (0, 100),
            "credit_score": (300, 850),
            "orig_dti": (0.000001, 65),
            "orig_cltv": (1, 998),
            "orig_ltv": (1, 998),
            "prior_dq_1": (0, 100),
            "prior_dq_2": (0, 100),
            "worst_dq_6": (0, 100),
            "worst_dq_12": (0, 100),
            "dq_months_6": (0, 6),
            "dq_months_12": (0, 12),
            "complete_status_6": (0, 1),
            "complete_status_12": (0, 1),
            "months_since_known_dq_12": (1, 12),
            "upb_change_ratio_3": (-1, 1e10),
            "upb_change_ratio_12": (-1, 1e10),
        }
        required = ("upb", "complete_status_6", "complete_status_12")
        if any(payload.features[name] is None for name in required):
            raise HTTPException(
                status_code=422, detail="Required current/completeness values missing"
            )
        for name, value in payload.features.items():
            if value is not None and not ranges[name][0] <= value <= ranges[name][1]:
                raise HTTPException(status_code=422, detail="Feature outside research domain range")
            if (
                value is not None
                and ("dq" in name or "complete_status" in name)
                and value != int(value)
            ):
                raise HTTPException(status_code=422, detail="Integer status/count feature required")
        for window in (6, 12):
            complete = payload.features[f"complete_status_{window}"]
            pair = (payload.features[f"worst_dq_{window}"], payload.features[f"dq_months_{window}"])
            if (complete == 0 and any(v is not None for v in pair)) or (
                complete == 1 and any(v is None for v in pair)
            ):
                raise HTTPException(
                    status_code=422, detail="History completeness and missing values disagree"
                )
        values = np.array(
            [[payload.features[name] for name in bundle["features"]]], dtype=np.float32
        )
        if np.isinf(values).any():
            raise HTTPException(status_code=422, detail="Feature outside float32 range")
        frame = pd.DataFrame(values, columns=bundle["features"])
        with model_lock, threadpool_limits(limits=2):
            probability = float(model.predict_proba(frame)[0, 1])
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise HTTPException(status_code=503, detail="Research model output unavailable")
        request.state.audit_probability = probability
        return {
            "request_id": request.state.request_id,
            "probability": probability,
            "horizon_months": 3,
            "model_id": bundle["model_id"],
            "scope": RESEARCH_SCOPE,
            "production_scoring_release": "HOLD",
            "public_scoring_authorized": False,
        }

    return app


def validate_tls_pair(cert_file: Path | None, key_file: Path | None) -> None:
    """Require a complete bounded private certificate/key pair before loading a model.

    Args:
        cert_file: Optional owner-only certificate chain outside the repository.
        key_file: Matching owner-only PEM private key outside the repository.

    Raises:
        ValueError: Partial pair, unsafe path or oversized certificate/key input.
        ssl.SSLError: Invalid certificate or mismatched key.
    """
    if cert_file is None and key_file is None:
        return
    if cert_file is None or key_file is None:
        raise ValueError("Both TLS certificate and private key are required")
    for path in (cert_file, key_file):
        private_file(path)
        if path.stat().st_size > 32768:
            raise ValueError("Bounded TLS certificate and key required")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)


def main() -> None:
    """Serve only on127.0.0.1 with a token read from an owner-only file, never printed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--audit-db", type=Path)
    parser.add_argument("--tls-cert-file", type=Path)
    parser.add_argument("--tls-key-file", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    for path in (args.bundle, args.token_file):
        if repo in path.resolve().parents or path.stat().st_mode & 0o077:
            raise ValueError("Bundle and credential must be owner-only and outside Git")
    if not 1024 <= args.port <= 65535:
        raise ValueError("Invalid research port")
    validate_tls_pair(args.tls_cert_file, args.tls_key_file)
    print("Memeriksa bundle model riset privat...", flush=True)
    app = create_app(args.bundle, args.token_file.read_text().strip(), args.audit_db)
    print(
        "Bundle terverifikasi. Memulai API lokal; tunggu pesan 'Uvicorn running on'. "
        "Biarkan terminal ini terbuka dan gunakan terminal kedua untuk mencoba scoring. "
        "Ctrl+C menghentikan server.",
        flush=True,
    )
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        log_level="info",
        ssl_certfile=str(args.tls_cert_file) if args.tls_cert_file else None,
        ssl_keyfile=str(args.tls_key_file) if args.tls_key_file else None,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
    )


if __name__ == "__main__":
    main()
