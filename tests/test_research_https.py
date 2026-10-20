"""Real certificate-chain/IP validation on toy HTTPS plus private TLS startup boundaries."""

from __future__ import annotations

import json
import shutil
import ssl
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from scripts.smoke_research_https import TLS_PROBE, generate_test_certificate
from src.research.freddie_monthly_adapter import MonthlySnapshot
from src.research.freddie_monthly_client import score_snapshot
from src.research.freddie_shadow_api import RESEARCH_SCOPE, main, validate_tls_pair
from tests.test_freddie_monthly_adapter import snapshot_data

TOKEN = "synthetic-only-test-credential-that-is-not-a-real-key"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    assert shutil.which("openssl"), "OpenSSL is required for transport contract tests"
    parent = tmp_path_factory.mktemp("tls-certificates")
    parent.chmod(0o700)
    cert, key = generate_test_certificate(parent / "valid")
    wrong_ca, wrong_key = generate_test_certificate(parent / "untrusted")
    bad_cert, bad_key = generate_test_certificate(parent / "wrong-host", "DNS:wrong.invalid")
    return {
        "cert": cert,
        "key": key,
        "wrong_ca": wrong_ca,
        "wrong_key": wrong_key,
        "bad_cert": bad_cert,
        "bad_key": bad_key,
    }


@contextmanager
def toy_server(cert: Path, key: Path, redirect: bool = False) -> Iterator[tuple[int, list[Any]]]:
    """Serve strict toy research responses over a genuine local TLS connection."""
    calls: list[Any] = []
    base = {
        "scope": RESEARCH_SCOPE,
        "production_scoring_release": "HOLD",
        "public_scoring_authorized": False,
        "model_id": "synthetic-model",
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def respond(self, body: dict[str, Any]) -> None:
            self.send_response(302 if redirect else 200)
            self.send_header("Content-Type", "application/json")
            if redirect:
                self.send_header("Location", "https://example.invalid/must-not-follow")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_GET(self) -> None:
            calls.append(("GET", self.path))
            self.respond({**base, "research_ready": True})

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(("POST", self.path, body))
            self.respond(
                {**base, "probability": 0.125, "horizon_months": 3, "request_id": str(uuid4())}
            )

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_verified_https_scores_and_transmits_only_features(certificates: dict[str, Path]) -> None:
    with toy_server(certificates["cert"], certificates["key"]) as (port, calls):
        result = score_snapshot(
            MonthlySnapshot.model_validate_json(json.dumps(snapshot_data())),
            TOKEN,
            port,
            ca_file=certificates["cert"],
        )
    assert result["probability"] == 0.125
    assert result["transport"] == "https" and result["tls_peer_verification_enabled"] is True
    assert calls[0] == ("GET", "/ready")
    assert set(calls[1][2]) == {"features"} and "loan_key" not in calls[1][2]["features"]
    assert result["production_scoring_release"] == "HOLD"


@pytest.mark.parametrize("mutation", ["untrusted", "hostname"])
def test_wrong_trust_or_ip_is_rejected_before_any_http_request(
    certificates: dict[str, Path], mutation: str
) -> None:
    cert = certificates["bad_cert"] if mutation == "hostname" else certificates["cert"]
    key = certificates["bad_key"] if mutation == "hostname" else certificates["key"]
    ca = certificates["bad_cert"] if mutation == "hostname" else certificates["wrong_ca"]
    with toy_server(cert, key) as (port, calls):
        with pytest.raises(ssl.SSLCertVerificationError):
            score_snapshot(
                MonthlySnapshot.model_validate_json(json.dumps(snapshot_data())),
                TOKEN,
                port,
                ca_file=ca,
            )
        assert calls == []


def test_https_redirect_is_not_followed(certificates: dict[str, Path]) -> None:
    with toy_server(certificates["cert"], certificates["key"], redirect=True) as (port, calls):
        with pytest.raises(ValueError, match="HTTP 302"):
            score_snapshot(
                MonthlySnapshot.model_validate_json(json.dumps(snapshot_data())),
                TOKEN,
                port,
                ca_file=certificates["cert"],
            )
        assert calls == [("GET", "/ready")]


@pytest.mark.parametrize("missing", ["cert", "key"])
def test_partial_tls_pair_is_rejected(certificates: dict[str, Path], missing: str) -> None:
    with pytest.raises(ValueError, match="Both TLS"):
        validate_tls_pair(
            None if missing == "cert" else certificates["cert"],
            None if missing == "key" else certificates["key"],
        )


def test_mismatched_key_is_rejected(certificates: dict[str, Path]) -> None:
    with pytest.raises(ssl.SSLError):
        validate_tls_pair(certificates["cert"], certificates["wrong_key"])
    validate_tls_pair(certificates["cert"], certificates["key"])
    validate_tls_pair(None, None)


@pytest.mark.parametrize("mutation", ["permissions", "oversized", "symlink"])
def test_unsafe_tls_file_is_rejected(
    certificates: dict[str, Path], tmp_path: Path, mutation: str
) -> None:
    path = tmp_path / "cert.pem"
    if mutation == "symlink":
        path.symlink_to(certificates["cert"])
    else:
        path.write_bytes(
            certificates["cert"].read_bytes() if mutation != "oversized" else b"x" * 32769
        )
        path.chmod(0o644 if mutation == "permissions" else 0o600)
    with pytest.raises(ValueError):
        validate_tls_pair(path, certificates["key"])


def test_partial_tls_cli_stops_before_loading_model(
    certificates: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, token = tmp_path / "bundle.json", tmp_path / "token.txt"
    for path in (bundle, token):
        path.write_text("synthetic input never loaded")
        path.chmod(0o600)
    monkeypatch.setattr(
        "sys.argv",
        [
            "api",
            "--bundle",
            str(bundle),
            "--token-file",
            str(token),
            "--tls-cert-file",
            str(certificates["cert"]),
        ],
    )
    with pytest.raises(ValueError, match="Both TLS"):
        main()


def test_tls_probe_syntax_and_container_start_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.smoke_research_api import _start

    compile(TLS_PROBE, "tls-probe", "exec")
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr("scripts.smoke_research_api._docker", lambda *args: calls.append(args))
    _start("image", tmp_path / "package", "owned", "owner", tmp_path / "state", tls=True)
    assert "--tls-cert-file" in calls[0] and "--tls-key-file" in calls[0]
    assert "--no-healthcheck" in calls[0]
    with pytest.raises(ValueError, match="audit directory"):
        _start("image", tmp_path / "package", "owned", "owner", tls=True)
