"""Verify private v4 API image, synthetic parity and restart recovery without source access."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from scripts.research_image_source_hash import source_tree_sha256
from src.research.freddie_monthly_adapter import MonthlySnapshot, build_feature_request
from src.research.freddie_preflight import read_object, sha256
from src.research.freddie_shadow_api import RESEARCH_SCOPE, verify_bundle

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-12
PROBE = r"""
import concurrent.futures, importlib.metadata, json, math, platform, statistics, sys, time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
folder=Path('/run/research')
token=(folder/'api_token.txt').read_text().strip()
features=json.loads((folder/'features.json').read_text())
def call(route='/score', body=None, authorized=True):
    headers={'Content-Type':'application/json'}
    if authorized: headers['Authorization']='Bearer '+token
    if body is None and route=='/score': body=json.dumps(features).encode()
    started=time.perf_counter()
    request=Request('http://127.0.0.1:8001'+route,data=body,headers=headers)
    try:
        with urlopen(request,timeout=10) as response:
            status=response.status
            data=json.loads(response.read())
    except HTTPError as error:
        status=error.code
        data={}
    return {'status':status,'body':data,'milliseconds':(time.perf_counter()-started)*1000}
action=sys.argv[1]
if action=='ready': result=call('/ready')
elif action=='score': result=call()
elif action=='unauthorized': result=call('/ready',authorized=False)
elif action=='invalid':
    features['features']['upb']=-1
    result=call(body=json.dumps(features).encode())
elif action=='oversized': result=call(body=b'x'*8193)
elif action=='measure':
    for _ in range(2): assert call()['status']==200
    result={}
    for concurrency in (1,2):
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            rows=list(pool.map(lambda _:call(),range(12)))
        timings=sorted(row['milliseconds'] for row in rows)
        result[str(concurrency)]={'requests':len(rows),
            'failures':sum(row['status']!=200 for row in rows),
            'p50_internal_http_ms':statistics.median(timings),
            'p95_internal_http_ms':timings[math.ceil(.95*len(timings))-1],
            'maximum_internal_http_ms':max(timings)}
    result['versions']={name:importlib.metadata.version(name) for name in
        ('numpy','pandas','scikit-learn','scipy','fastapi','uvicorn','pydantic','joblib','threadpoolctl')}
    status=Path('/proc/1/status').read_text().splitlines()
    rss=next(line.split()[1] for line in status if line.startswith('VmHWM:'))
    result['process_peak_rss_kib']=int(rss)
    result['python']=platform.python_version()
    result['machine']=platform.machine()
else: raise ValueError('Unsupported private probe')
print(json.dumps(result,allow_nan=False))
"""


def _private(path: Path) -> None:
    resolved = path.resolve()
    if ROOT == resolved or ROOT in resolved.parents:
        raise ValueError("Private artifacts must remain outside the repository")
    if path.exists() and path.stat().st_mode & 0o077:
        raise ValueError("Owner-only private artifact permissions required")


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    path.chmod(0o600)


def stage_bundle(bundle_path: Path, token_path: Path, snapshot_path: Path, output: Path) -> float:
    """Stage only bound serving artifacts and synthetic input in a fresh private directory.

    Args:
        bundle_path: Trusted accepted research manifest; never an arbitrary user model.
        token_path: Existing owner-only API credential file.
        snapshot_path: Owner-supplied synthetic normalized monthly request.
        output: Fresh directory outside Git; existing evidence is not overwritten.

    Returns:
        Native accepted-model probability for the synthetic request.

    Raises:
        ValueError: Private boundary, evidence or credential validation fails.
        FileExistsError: Staging directory already exists.
    """
    for path in (bundle_path, token_path, snapshot_path, output):
        _private(path)
    if len(token_path.read_text().strip()) < 32 or token_path.stat().st_size > 4096:
        raise ValueError("Bounded private token required")
    if snapshot_path.stat().st_size > 131072:
        raise ValueError("Bounded synthetic snapshot required")
    bundle, model = verify_bundle(bundle_path)
    snapshot = MonthlySnapshot.model_validate_json(snapshot_path.read_bytes())
    payload = build_feature_request(snapshot)
    frame = pd.DataFrame(
        np.array([list(payload["features"].values())], dtype=np.float32),
        columns=bundle["features"],
    )
    with threadpool_limits(limits=2):
        probability = float(model.predict_proba(frame)[0, 1])
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Invalid native probability")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    for role in ("validation", "test"):
        (output / role).mkdir(mode=0o700)
    sources = (
        (
            Path(bundle["validation_run"]) / "candidate_pipeline.joblib",
            "validation/candidate_pipeline.joblib",
            bundle["candidate_sha256"],
        ),
        (
            Path(bundle["validation_run"]) / "validation_report.json",
            "validation/validation_report.json",
            bundle["validation_report_sha256"],
        ),
        (
            Path(bundle["test_run"]) / "test_report.json",
            "test/test_report.json",
            bundle["test_report_sha256"],
        ),
    )
    for source, relative, expected in sources:
        target = output / relative
        shutil.copyfile(source, target)
        target.chmod(0o600)
        if sha256(target) != expected:
            raise ValueError("Copied serving artifact checksum mismatch")
    relocated = dict(bundle)
    relocated.update(
        protocol_path="/app/config/research/freddie_experiment_v4.json",
        execution_path="/app/config/research/freddie_independent_test_v4.json",
        validation_run="/run/research/validation",
        test_run="/run/research/test",
    )
    _write(output / "bundle_manifest.json", relocated)
    _write(output / "features.json", payload)
    shutil.copyfile(token_path, output / "api_token.txt")
    (output / "api_token.txt").chmod(0o600)
    return probability


def _docker(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, check=check, timeout=90
    )


def _probe(container: str, action: str) -> dict[str, Any]:
    return dict(json.loads(_docker("exec", container, "python", "-c", PROBE, action).stdout))


def _start(
    image: str,
    package: Path,
    name: str,
    owner: str,
    audit_directory: Path | None = None,
    tls: bool = False,
) -> str:
    audit_mount = (
        []
        if audit_directory is None
        else [
            "--no-healthcheck",
            "--mount",
            f"type=bind,src={audit_directory.resolve()},dst=/run/audit",
        ]
    )
    audit_arguments = (
        []
        if audit_directory is None
        else [
            "--bundle",
            "/run/research/bundle_manifest.json",
            "--token-file",
            "/run/research/api_token.txt",
            "--port",
            "8001",
            "--audit-db",
            "/run/audit/audit.sqlite",
        ]
    )
    if tls:
        if audit_directory is None:
            raise ValueError("TLS acceptance requires its private audit directory")
        audit_arguments.extend(
            [
                "--tls-cert-file",
                "/run/research/tls_cert.pem",
                "--tls-key-file",
                "/run/research/tls_key.pem",
            ]
        )
    _docker(
        "run",
        "--detach",
        "--name",
        name,
        "--label",
        "creditlens.acceptance=" + owner,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--pids-limit",
        "128",
        "--tmpfs",
        "/tmp:rw,size=16777216,mode=1777",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={package.resolve()},dst=/run/research,readonly",
        *audit_mount,
        image,
        *audit_arguments,
    )
    return name


def _wait_ready(container: str) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            result = _probe(container, "ready")
            if result["status"] == 200 and result["body"]["research_ready"] is True:
                return result
        except (subprocess.CalledProcessError, ValueError, KeyError):
            state = json.loads(_docker("inspect", container).stdout)[0]["State"]
            if not state["Running"]:
                raise ValueError("Container exited before research readiness") from None
        time.sleep(1)
    raise TimeoutError("Research readiness timed out")


def _require_score(result: dict[str, Any], expected: float, model_id: str) -> None:
    body = result["body"]
    if (
        result["status"] != 200
        or body.get("model_id") != model_id
        or body.get("scope") != RESEARCH_SCOPE
        or body.get("horizon_months") != 3
        or body.get("production_scoring_release") != "HOLD"
        or body.get("public_scoring_authorized") is not False
        or type(body.get("probability")) not in (int, float)
        or not math.isfinite(body["probability"])
        or abs(body["probability"] - expected) > TOLERANCE
    ):
        raise ValueError("Container/native research parity failed")


def run_acceptance(
    image: str, bundle: Path, token: Path, snapshot: Path, output: Path
) -> dict[str, Any]:
    """Verify an isolated image and recovery, keeping failed evidence and owned cleanup.

    Args:
        image: Locally built research image tag or ID, never pushed by this runner.
        bundle: Existing accepted private serving manifest.
        token: Owner-only credential file.
        snapshot: Explicitly synthetic private monthly request, not source records.
        output: Fresh private receipt directory, never an existing run.

    Returns:
        Verified container acceptance receipt; production remains HOLD.

    Raises:
        ValueError: Scope, image, boundary, parity or recovery check fails.
        subprocess.SubprocessError: Docker operation fails.
    """
    _private(output)
    if os.getuid() == 0 or shutil.disk_usage(ROOT).free < 8 * 1024**3:
        raise ValueError("Non-root owner and at least8GiB free space required")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "status": "RUNNING",
        "verified_at": datetime.now(UTC).isoformat(),
        "production_scoring_release": "HOLD",
        "synthetic_input_declared_by_operator": True,
        "test_archive_opened": False,
        "model_fitting_performed": False,
    }
    owner = uuid4().hex
    names: list[str] = []
    try:
        native = stage_bundle(bundle, token, snapshot, output / "package")
        staged = read_object(output / "package/bundle_manifest.json")
        inspected = json.loads(_docker("image", "inspect", image).stdout)[0]
        image_id = inspected["Id"]
        labels = inspected["Config"]["Labels"]
        if labels.get("org.creditlens.scope") != "private-mortgage-research" or labels.get(
            "org.creditlens.source-tree-sha256"
        ) != source_tree_sha256(ROOT):
            raise ValueError("Image public source identity mismatch")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ValueError("Immutable local image ID required")
        # Inspect image filesystem without any private mounts before running the model.
        scan = (
            "from pathlib import Path; p=Path('/app'); "
            "bad=[str(x) for x in p.rglob('*') "
            "if x.name in ('.git','.env','api_token.txt') "
            "or x.suffix in ('.joblib','.zip','.csv','.gz','.sqlite')]; "
            "assert not bad; assert not Path('/run/research').exists(); print('clean')"
        )
        clean = _docker(
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--entrypoint",
            "python",
            image_id,
            "-c",
            scan,
        )
        if clean.stdout.strip() != "clean":
            raise ValueError("Private artifacts present in image")
        baseline = "creditlens-research-" + owner + "-baseline"
        names.append(baseline)
        _start(image_id, output / "package", baseline, owner)
        ready = _wait_ready(baseline)
        actual = _probe(baseline, "score")
        _require_score(actual, native, staged["model_id"])
        statuses = {
            action: _probe(baseline, action)["status"]
            for action in ("unauthorized", "invalid", "oversized")
        }
        if statuses != {"unauthorized": 401, "invalid": 422, "oversized": 413}:
            raise ValueError("Container negative request contract failed")
        workload = _probe(baseline, "measure")
        if any(workload[str(n)]["failures"] for n in (1, 2)):
            raise ValueError("Diagnostic workload failed")
        if (
            workload["versions"]["scikit-learn"] != staged["sklearn"]
            or workload["versions"]["numpy"] != staged["numpy"]
        ):
            raise ValueError("Container runtime differs from admitted bundle")
        runtime = json.loads(_docker("inspect", baseline).stdout)[0]
        constraints = runtime["HostConfig"]
        if (
            constraints["NetworkMode"] != "none"
            or not constraints["ReadonlyRootfs"]
            or runtime["NetworkSettings"]["Ports"]
            or constraints["CapDrop"] != ["ALL"]
            or runtime["Config"]["User"] != f"{os.getuid()}:{os.getgid()}"
            or "no-new-privileges" not in constraints["SecurityOpt"]
            or constraints["PidsLimit"] != 128
            or constraints["Memory"] != 2 * 1024**3
            or constraints["NanoCpus"] != 2 * 10**9
            or not all(not mount["RW"] for mount in runtime["Mounts"] if mount["Type"] == "bind")
        ):
            raise ValueError("Container isolation contract failed")
        _docker("stop", "--time", "10", baseline)
        bad_package = output / "bad-package"
        shutil.copytree(output / "package", bad_package)
        bad = dict(staged)
        bad["candidate_sha256"] = "0" * 64
        _write(bad_package / "bundle_manifest.json", bad)
        failing = "creditlens-research-" + owner + "-rejected"
        names.append(failing)
        recovery_started = time.monotonic()
        _start(image_id, bad_package, failing, owner)
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            state = json.loads(_docker("inspect", failing).stdout)[0]["State"]
            if not state["Running"]:
                break
            time.sleep(1)
        else:
            raise ValueError("Corrupt manifest did not fail startup")
        if state["ExitCode"] == 0:
            raise ValueError("Corrupt manifest exited successfully")
        restored = "creditlens-research-" + owner + "-restored"
        names.append(restored)
        _start(image_id, output / "package", restored, owner)
        _wait_ready(restored)
        _require_score(_probe(restored, "score"), native, staged["model_id"])
        receipt.update(
            status="PASS_LOCAL_CONTAINER_RESEARCH",
            image_id=image_id,
            image_os=inspected["Os"],
            image_architecture=inspected["Architecture"],
            base_image_reference=(ROOT / "infra/docker/Dockerfile.research-api")
            .read_text()
            .splitlines()[1]
            .removeprefix("FROM "),
            requirements_sha256=sha256(ROOT / "infra/docker/requirements.research-api.txt"),
            source_tree_sha256=inspected["Config"]["Labels"].get(
                "org.creditlens.source-tree-sha256"
            ),
            verification_script_sha256=sha256(Path(__file__)),
            candidate_sha256=staged["candidate_sha256"],
            original_bundle_sha256=sha256(bundle),
            relocated_bundle_sha256=sha256(output / "package/bundle_manifest.json"),
            monthly_snapshot_sha256=sha256(snapshot),
            absolute_parity_difference=abs(actual["body"]["probability"] - native),
            parity_tolerance=TOLERANCE,
            ready_http=ready["status"],
            negative_statuses=statuses,
            diagnostic_workload=workload,
            corrupt_bundle_exit_code=state["ExitCode"],
            restart_recovery_seconds=time.monotonic() - recovery_started,
            public_ingress_tested=False,
            operating_slo_accepted=False,
            operational_point_in_time_verified=False,
        )
    except BaseException as error:
        receipt.update(status="FAILED", failure_type=type(error).__name__)
        raise
    finally:
        cleanup_failed = []
        for name in names:
            try:
                inspected_run = _docker("inspect", name, check=False)
                if inspected_run.returncode:
                    continue
                info = json.loads(inspected_run.stdout)[0]
                if info["Config"]["Labels"].get("creditlens.acceptance") != owner:
                    cleanup_failed.append(name)
                    continue
                logs = _docker("logs", name, check=False)
                log_path = output / (name.rsplit("-", 1)[-1] + ".log")
                safe_log = (logs.stdout + logs.stderr).replace(
                    token.read_text().strip(), "[REDACTED]"
                )
                log_path.write_text(safe_log)
                log_path.chmod(0o600)
                if _docker("rm", "--force", name, check=False).returncode:
                    cleanup_failed.append(name)
            except (subprocess.SubprocessError, OSError, ValueError, KeyError):
                cleanup_failed.append(name)
        receipt["test_owned_containers_removed"] = not cleanup_failed
        if cleanup_failed:
            receipt["status"] = "FAILED_CLEANUP"
        _write(output / "receipt.json", receipt)
    if receipt["status"] != "PASS_LOCAL_CONTAINER_RESEARCH":
        raise ValueError("Acceptance or owned-container cleanup failed")
    return receipt


def main() -> None:
    """Run local synthetic container acceptance and print only status and private report path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-synthetic", action="store_true", required=True)
    args = parser.parse_args()
    result = run_acceptance(args.image, args.bundle, args.token_file, args.snapshot, args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "production_scoring_release": "HOLD",
                "receipt": str(args.output / "receipt.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
