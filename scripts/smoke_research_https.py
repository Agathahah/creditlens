"""Private accepted-model HTTPS, certificate rejection and restart-based credential rotation."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.research_image_source_hash import source_tree_sha256
from scripts.research_journal_backup import _fresh_directory, assert_preserved, inspect_journal
from scripts.smoke_research_api import ROOT, _docker, _require_score, _start, _write, stage_bundle
from src.research.freddie_monthly_adapter import MonthlySnapshot
from src.research.freddie_monthly_client import score_snapshot
from src.research.freddie_preflight import sha256
from src.research.freddie_shadow_api import validate_tls_pair

TLS_PROBE = r"""
import http.client,json,ssl,sys
from pathlib import Path
p=Path('/run/research'); action=sys.argv[1]
ca=p/('untrusted_cert.pem' if action=='wrong-ca' else 'tls_cert.pem')
token=(p/('retired_token.txt' if action=='retired' else 'api_token.txt')).read_text().strip()
if action=='plain': c=http.client.HTTPConnection('127.0.0.1',8001,timeout=10)
else: c=http.client.HTTPSConnection('127.0.0.1',8001,timeout=10,
    context=ssl.create_default_context(cafile=ca))
try:
    try:
        c.connect()
        version=None if action=='plain' else c.sock.version()
        score=action in ('score','plain')
        c.request('POST' if score else 'GET','/score' if score else '/ready',
            (p/'features.json').read_bytes() if score else None,
            {'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        r=c.getresponse(); body=json.loads(r.read(8193))
        result={'status':r.status,'body':body,'tls_version':version}
    except ssl.SSLCertVerificationError as e:
        if action!='wrong-ca': raise
        result={'certificate_rejected':True,'verify_code':e.verify_code}
    except (OSError,http.client.HTTPException):
        if action!='plain': raise
        result={'plaintext_rejected':True}
finally: c.close()
print(json.dumps(result,allow_nan=False))
"""


def generate_test_certificate(folder: Path, san: str = "IP:127.0.0.1") -> tuple[Path, Path]:
    """Generate a short-lived private test-only trust anchor; never alter the OS trust store.

    Args:
        folder: Fresh private directory outside Git.
        san: Loopback IP or deliberately mismatched DNS identity for a negative test.

    Returns:
        Owner-only PEM certificate and matching private-key paths.

    Raises:
        ValueError: Unsafe output or unexpected test identity.
        subprocess.SubprocessError: OpenSSL fails or exceeds the bounded generation time.
    """
    if san not in ("IP:127.0.0.1", "DNS:wrong.invalid"):
        raise ValueError("Fixed local test identities only")
    _fresh_directory(folder)
    cert, key = folder / "cert.pem", folder / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "7",
            "-subj",
            "/CN=CreditLens private local test",
            "-addext",
            "subjectAltName=" + san,
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
        timeout=30,
        umask=0o077,
    )
    cert.chmod(0o600)
    key.chmod(0o600)
    validate_tls_pair(cert, key)
    return cert, key


def _secret(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".new")
    with temporary.open("x") as handle:
        temporary.chmod(0o600)
        handle.write(value)
    temporary.replace(path)


def _native_probe(port: int, ca: Path, token: str, plain: bool = False) -> dict[str, Any]:
    connection: http.client.HTTPConnection
    connection = (
        http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        if plain
        else http.client.HTTPSConnection(
            "127.0.0.1", port, timeout=10, context=ssl.create_default_context(cafile=ca)
        )
    )
    try:
        connection.connect()
        version = None if plain else connection.sock.version()  # type: ignore[union-attr]
        connection.request("GET", "/ready", headers={"Authorization": "Bearer " + token})
        response = connection.getresponse()
        return {
            "status": response.status,
            "body": json.loads(response.read(8193)),
            "tls_version": version,
        }
    finally:
        connection.close()


@contextmanager
def _native_server(
    bundle: Path, token: Path, cert: Path, key: Path, state: Path, log: Path, mismatch: bool = False
) -> Iterator[int]:
    with socket.socket() as free_port:
        free_port.bind(("127.0.0.1", 0))
        port = free_port.getsockname()[1]
    with log.open("wb") as stream:
        log.chmod(0o600)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.research.freddie_shadow_api",
                "--bundle",
                str(bundle),
                "--token-file",
                str(token),
                "--audit-db",
                str(state),
                "--port",
                str(port),
                "--tls-cert-file",
                str(cert),
                "--tls-key-file",
                str(key),
            ],
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            env={**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"},
        )
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise ValueError("Native TLS server exited before readiness")
                try:
                    result = _native_probe(port, cert, token.read_text().strip())
                    if not mismatch and result["status"] == 200:
                        break
                except ssl.SSLCertVerificationError:
                    if mismatch:
                        break
                    raise
                except (OSError, http.client.HTTPException):
                    pass
                time.sleep(0.25)
            else:
                raise TimeoutError("Native TLS readiness timed out")
            yield port
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def _persisted(path: Path, request_id: str) -> None:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT status FROM events WHERE request_id=?", (request_id,)
        ).fetchone()
    if row != (200,):
        raise ValueError("Successful TLS score was not persisted")


def run_transport_acceptance(
    image: str,
    bundle: Path,
    snapshot_path: Path,
    output: Path,
    origin: str = "local_command_unverified_identity",
) -> dict[str, Any]:
    """Verify native/container TLS and test-only credential rotation on the accepted candidate.

    Args:
        image: Current local software-only research image.
        bundle: Existing accepted private manifest; never modified.
        snapshot_path: Declared synthetic monthly input, never a source archive.
        output: Fresh owner-only directory outside Git.
        origin: Assistant check or unverified local command identity.

    Returns:
        Private receipt only after all transport, trust and credential checks pass.

    Raises:
        ValueError: Private boundary, source, parity, TLS, rotation or cleanup mismatch.
        subprocess.SubprocessError: Native/OpenSSL/Docker operation fails.
    """
    if os.getuid() == 0 or shutil.disk_usage(ROOT).free < 8 * 1024**3:
        raise ValueError("Non-root owner and at least8GiB free space required")
    _fresh_directory(output)
    receipt: dict[str, Any] = {
        "status": "RUNNING",
        "started_at": datetime.now(UTC).isoformat(),
        "execution_origin": origin,
        "production_scoring_release": "HOLD",
        "operational_pilot_admission": "NOT_ADMITTED",
        "operational_quality_verified": False,
        "test_only_credentials": True,
        "source_archives_opened": False,
        "training_or_test_rerun": False,
        "verification_script_sha256": sha256(Path(__file__)),
        "container_helper_sha256": sha256(ROOT / "scripts/smoke_research_api.py"),
    }
    owner, names = uuid4().hex, []
    a, b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    try:
        cert, key = generate_test_certificate(output / "serving-cert")
        wrong_ca, _ = generate_test_certificate(output / "wrong-ca")
        bad_cert, bad_key = generate_test_certificate(output / "wrong-host", "DNS:wrong.invalid")
        token = output / "native_token.txt"
        _secret(token, a)
        native = stage_bundle(bundle, token, snapshot_path, output / "package")
        snapshot = MonthlySnapshot.model_validate_json(snapshot_path.read_bytes())
        model_id = json.loads((output / "package/bundle_manifest.json").read_text())["model_id"]
        state = output / "native-state/audit.sqlite"
        state.parent.mkdir(mode=0o700)
        with _native_server(bundle, token, cert, key, state, output / "native-a.log") as port:
            score = score_snapshot(snapshot, a, port, ca_file=cert)
            _require_score({"status": 200, "body": score}, native, model_id)
            _persisted(state, score["request_id"])
            native_tls = _native_probe(port, cert, a)["tls_version"]
            try:
                _native_probe(port, wrong_ca, a)
            except ssl.SSLCertVerificationError:
                receipt["native_wrong_ca_rejected"] = True
            else:
                raise ValueError("Untrusted CA accepted")
            try:
                plain = _native_probe(port, cert, a, plain=True)
            except (OSError, http.client.HTTPException):
                receipt["native_plaintext_rejected"] = True
            else:
                if plain["status"] == 200:
                    raise ValueError("Plaintext unexpectedly succeeded")
                receipt["native_plaintext_rejected"] = True
            before = inspect_journal(state)
        _secret(token, b)
        native_rotation = time.monotonic()
        with _native_server(bundle, token, cert, key, state, output / "native-b.log") as port:
            if _native_probe(port, cert, a)["status"] != 401:
                raise ValueError("Retired native token accepted")
            score = score_snapshot(snapshot, b, port, ca_file=cert)
            _require_score({"status": 200, "body": score}, native, model_id)
            _persisted(state, score["request_id"])
            assert_preserved(state, before)
            native_rotation = time.monotonic() - native_rotation
        with _native_server(
            bundle, token, bad_cert, bad_key, state, output / "native-hostname.log", True
        ) as port:
            try:
                _native_probe(port, bad_cert, b)
            except ssl.SSLCertVerificationError as error:
                if "mismatch" not in error.verify_message.lower():
                    raise
                receipt["native_hostname_mismatch_rejected"] = True
            else:
                raise ValueError("Incorrect certificate identity accepted")
        info = json.loads(_docker("image", "inspect", image).stdout)[0]
        image_id = info["Id"]
        if (
            info["Config"]["Labels"].get("org.creditlens.source-tree-sha256")
            != source_tree_sha256(ROOT)
            or info["Config"]["Labels"].get("org.creditlens.scope") != "private-mortgage-research"
        ):
            raise ValueError("Image source/scope mismatch")
        package = output / "package"
        for source, target in (
            (cert, "tls_cert.pem"),
            (key, "tls_key.pem"),
            (wrong_ca, "untrusted_cert.pem"),
        ):
            shutil.copyfile(source, package / target)
            (package / target).chmod(0o600)
        _secret(package / "retired_token.txt", a)
        audit = output / "container-state"
        audit.mkdir(mode=0o700)

        def probe(name: str, action: str) -> dict[str, Any]:
            return dict(json.loads(_docker("exec", name, "python", "-c", TLS_PROBE, action).stdout))

        def ready(name: str) -> dict[str, Any]:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                try:
                    result = probe(name, "ready")
                    if result["status"] == 200 and result["body"].get("audit_enabled") is True:
                        return result
                except subprocess.CalledProcessError:
                    if not json.loads(_docker("inspect", name).stdout)[0]["State"]["Running"]:
                        raise ValueError("TLS container exited") from None
                time.sleep(0.5)
            raise TimeoutError("TLS container readiness timeout")

        first = "creditlens-tls-" + owner + "-first"
        names.append(first)
        _start(image_id, package, first, owner, audit, tls=True)
        result = ready(first)
        container_tls = result["tls_version"]
        scored = probe(first, "score")
        _require_score(scored, native, model_id)
        _persisted(audit / "audit.sqlite", scored["body"]["request_id"])
        if probe(first, "wrong-ca").get("certificate_rejected") is not True:
            raise ValueError("Container accepted incorrect CA")
        plain = probe(first, "plain")
        if not plain.get("plaintext_rejected") and plain.get("status") == 200:
            raise ValueError("Container plaintext unexpectedly succeeded")
        prefix = inspect_journal(audit / "audit.sqlite")
        _docker("stop", "--time", "10", first)
        _secret(package / "api_token.txt", b)
        container_rotation = time.monotonic()
        rotated = "creditlens-tls-" + owner + "-rotated"
        names.append(rotated)
        _start(image_id, package, rotated, owner, audit, tls=True)
        ready(rotated)
        if probe(rotated, "retired")["status"] != 401:
            raise ValueError("Retired Docker token accepted")
        scored = probe(rotated, "score")
        _require_score(scored, native, model_id)
        _persisted(audit / "audit.sqlite", scored["body"]["request_id"])
        assert_preserved(audit / "audit.sqlite", prefix)
        container_rotation = time.monotonic() - container_rotation
        if native_tls not in ("TLSv1.2", "TLSv1.3") or container_tls not in ("TLSv1.2", "TLSv1.3"):
            raise ValueError("Unexpected negotiated TLS version")
        receipt.update(
            status="PASS_PRIVATE_HTTPS_CREDENTIAL_ROTATION",
            image_id=image_id,
            public_source_sha256=source_tree_sha256(ROOT),
            original_bundle_sha256=sha256(bundle),
            synthetic_snapshot_sha256=sha256(snapshot_path),
            certificate_sha256=sha256(cert),
            candidate_sha256=json.loads((package / "bundle_manifest.json").read_text())[
                "candidate_sha256"
            ],
            native_tls_version=native_tls,
            container_tls_version=container_tls,
            container_wrong_ca_rejected=True,
            container_plaintext_rejected=True,
            native_retired_token_http=401,
            container_retired_token_http=401,
            new_token_score_http=200,
            earlier_journal_rows_preserved=True,
            native_restart_rotation_seconds=native_rotation,
            container_restart_rotation_seconds=container_rotation,
            self_signed_test_certificate=True,
            public_ingress_verified=False,
            production_identity_provider=False,
            native_owned_servers_stopped=True,
            owner_original_credential_modified=False,
        )
    except BaseException as error:
        receipt.update(status="FAILED", failure_type=type(error).__name__)
        raise
    finally:
        failures = []
        for name in names:
            try:
                found = _docker("inspect", name, check=False)
                if found.returncode:
                    continue
                if (
                    json.loads(found.stdout)[0]["Config"]["Labels"].get("creditlens.acceptance")
                    != owner
                ):
                    failures.append(name)
                    continue
                log = _docker("logs", name, check=False)
                text = (log.stdout + log.stderr).replace(a, "[REDACTED]").replace(b, "[REDACTED]")
                log_path = output / (name.rsplit("-", 1)[-1] + ".log")
                log_path.write_text(text)
                log_path.chmod(0o600)
                if _docker("rm", "--force", name, check=False).returncode:
                    failures.append(name)
            except Exception:
                failures.append(name)
        receipt["test_owned_containers_removed"] = not failures
        if failures:
            receipt["status"] = "FAILED_CLEANUP"
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        _write(output / "receipt.json", receipt)
    if receipt["status"] != "PASS_PRIVATE_HTTPS_CREDENTIAL_ROTATION":
        raise ValueError("Transport verification or owned cleanup failed")
    return receipt


def main() -> None:
    """Run declared synthetic transport verification without exposing certificates or secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    for option in ("bundle", "snapshot", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--confirm-synthetic", required=True, action="store_true")
    parser.add_argument("--assistant-check", action="store_true")
    args = parser.parse_args()
    run_transport_acceptance(
        args.image,
        args.bundle,
        args.snapshot,
        args.output,
        "assistant_check" if args.assistant_check else "local_command_unverified_identity",
    )
    print("Berhasil: HTTPS terverifikasi, sertifikat salah ditolak, dan rotasi token lulus.")
    print("Bukti privat:", args.output / "receipt.json")


if __name__ == "__main__":
    main()
