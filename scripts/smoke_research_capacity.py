"""Bounded accepted-model HTTPS concurrency, actual quota exhaustion and real-time recovery."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from scripts.research_image_source_hash import source_tree_sha256
from scripts.research_journal_backup import _fresh_directory, inspect_journal
from scripts.smoke_research_api import ROOT, _docker, _require_score, _start, _write, stage_bundle
from scripts.smoke_research_https import TLS_PROBE, _secret, generate_test_certificate
from src.research.freddie_preflight import sha256

CAPACITY_PROBE = r"""
import concurrent.futures,http.client,json,math,ssl,statistics,sys,time
from pathlib import Path
p=Path('/run/research'); token=(p/'api_token.txt').read_text().strip()
context=ssl.create_default_context(cafile=p/'tls_cert.pem')
features=(p/'features.json').read_bytes()
def call(authorized=True):
    c=http.client.HTTPSConnection('127.0.0.1',8001,timeout=10,context=context)
    started=time.perf_counter()
    try:
        c.connect(); version=c.sock.version()
        headers={'Content-Type':'application/json'}
        if authorized: headers['Authorization']='Bearer '+token
        c.request('POST','/score',features,headers)
        r=c.getresponse(); body=r.read(8193)
        if len(body)>8192: raise ValueError('Oversized response')
        return {'status':r.status,'body':json.loads(body),
            'request_id':r.getheader('X-Request-ID'),'tls_version':version,
            'milliseconds':(time.perf_counter()-started)*1000}
    finally: c.close()
def summarize(rows):
    times=sorted(r['milliseconds'] for r in rows)
    return {'requests':len(rows),'failures':sum(r['status']!=200 for r in rows),
        'p50_internal_https_ms':statistics.median(times),
        'p95_internal_https_ms':times[math.ceil(.95*len(times))-1],
        'p99_internal_https_ms':times[math.ceil(.99*len(times))-1],
        'maximum_internal_https_ms':max(times)}
if sys.argv[1]=='measure':
    rows=[call(),call()]; groups={}; started=time.monotonic()
    for n in (1,5):
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            group=list(pool.map(lambda _:call(),range(12)))
        groups[str(n)]=summarize(group); rows.extend(group)
    for _ in range(61):
        row=call(); rows.append(row)
        if row['status']==429: break
        if row['status']!=200: raise ValueError('Unexpected quota fill response')
    else: raise ValueError('Quota did not reject')
    for _ in range(4): rows.append(call())
    rows.append(call(False))
    status=Path('/proc/1/status').read_text().splitlines()
    rss=int(next(line.split()[1] for line in status if line.startswith('VmHWM:')))
    result={'rows':rows,'workload':groups,'fill_seconds':time.monotonic()-started,
        'process_peak_rss_kib':rss}
elif sys.argv[1]=='recover': result={'rows':[call()]}
else: raise ValueError('Fixed bounded action required')
print(json.dumps(result,allow_nan=False))
"""


def _workload(container: str, action: str) -> dict[str, Any]:
    result = subprocess.run(
        ["docker", "exec", container, "python", "-c", CAPACITY_PROBE, action],
        capture_output=True,
        text=True,
        check=True,
        timeout=30 if action == "measure" else 15,
    )
    return dict(json.loads(result.stdout))


def reconcile_requests(
    journal: Path, rows: list[dict[str, Any]], model_id: str, candidate_sha: str
) -> dict[str, int]:
    """Match observed HTTPS responses to committed events without exposing journal contents.

    Args:
        journal: Private bounded audit database from this run.
        rows: Observed request IDs, status and response bodies.
        model_id: Expected model identity from the accepted bundle.
        candidate_sha: Expected artifact digest from the same bundle.

    Returns:
        Reconciled response and successful-score counts.

    Raises:
        ValueError: Duplicate/missing ID, uncommitted result or rejection with probability.
    """
    inspect_journal(journal)
    seen: set[str] = set()
    scores = 0
    with closing(sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        for result in rows:
            identity = result.get("request_id")
            if not isinstance(identity, str) or str(UUID(identity)) != identity or identity in seen:
                raise ValueError("Unique canonical server request IDs required")
            seen.add(identity)
            row = db.execute(
                "SELECT status,probability,model_id,model_sha FROM events WHERE request_id=?",
                (identity,),
            ).fetchone()
            probability = result["body"].get("probability")
            if row != (result["status"], probability, model_id, candidate_sha):
                raise ValueError("Observed response does not match committed audit")
            if result["status"] == 200 and result["body"].get("request_id") != identity:
                raise ValueError("Response body/header request identities disagree")
            if result["status"] != 200 and probability is not None:
                raise ValueError("Rejected request must not include a probability")
            scores += int(result["status"] == 200)
    return {"observed_responses": len(rows), "persisted_scores": scores}


def run_capacity_acceptance(
    image: str,
    bundle: Path,
    snapshot: Path,
    output: Path,
    origin: str = "local_command_unverified_identity",
) -> dict[str, Any]:
    """Exercise the fixed local research envelope without changing quota or original artifacts.

    Args:
        image: Current source-bound local image ID.
        bundle: Trusted accepted private v4 manifest.
        snapshot: Explicitly synthetic monthly request outside Git.
        output: Fresh private output directory below an owner-only parent.
        origin: Assistant check or unverified local command identity.

    Returns:
        Private receipt only after parity, quota, recovery, audit and cleanup pass.

    Raises:
        ValueError: Source identity, parity, quota, audit or cleanup mismatch.
        subprocess.SubprocessError: Bounded Docker/OpenSSL verification fails.
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
        "source_archives_opened": False,
        "training_or_test_rerun": False,
        "verification_script_sha256": sha256(Path(__file__)),
        "container_helper_sha256": sha256(ROOT / "scripts/smoke_research_api.py"),
        "tls_helper_sha256": sha256(ROOT / "scripts/smoke_research_https.py"),
    }
    owner, token = uuid4().hex, secrets.token_urlsafe(32)
    name = "creditlens-capacity-" + owner
    try:
        info = json.loads(_docker("image", "inspect", image).stdout)[0]
        source = source_tree_sha256(ROOT)
        if (
            info["Config"]["Labels"].get("org.creditlens.source-tree-sha256") != source
            or info["Config"]["Labels"].get("org.creditlens.scope") != "private-mortgage-research"
        ):
            raise ValueError("Image source/scope mismatch")
        _secret(output / "test_token.txt", token)
        expected = stage_bundle(bundle, output / "test_token.txt", snapshot, output / "package")
        package = output / "package"
        manifest = json.loads((package / "bundle_manifest.json").read_text())
        model, candidate = manifest["model_id"], manifest["candidate_sha256"]
        cert, key = generate_test_certificate(output / "test-cert")
        for src, target in ((cert, "tls_cert.pem"), (key, "tls_key.pem")):
            shutil.copyfile(src, package / target)
            (package / target).chmod(0o600)
        audit = output / "state"
        audit.mkdir(mode=0o700)
        _start(info["Id"], package, name, owner, audit, tls=True)
        started = time.monotonic()
        while time.monotonic() - started < 40:
            probe = _docker("exec", name, "python", "-c", TLS_PROBE, "ready", check=False)
            if probe.returncode == 0:
                ready = json.loads(probe.stdout)
                if ready["status"] != 200 or ready["body"].get("audit_enabled") is not True:
                    raise ValueError("Audited TLS readiness failed")
                break
            if not json.loads(_docker("inspect", name).stdout)[0]["State"]["Running"]:
                raise ValueError("Research container exited before readiness")
            time.sleep(0.5)
        else:
            raise TimeoutError("Bounded TLS readiness timeout")
        measured = _workload(name, "measure")
        rows = measured["rows"]
        for row in rows:
            if row["tls_version"] not in ("TLSv1.2", "TLSv1.3"):
                raise ValueError("Unexpected TLS version")
            if row["status"] == 200:
                _require_score(row, expected, model)
        if (
            any(group["failures"] for group in measured["workload"].values())
            or [row["status"] for row in rows[-6:]] != [429] * 5 + [401]
            or measured["fill_seconds"] >= 60
        ):
            raise ValueError("Fixed workload or quota rejection failed")
        with closing(
            sqlite3.connect((audit / "audit.sqlite").as_uri() + "?mode=ro", uri=True)
        ) as db:
            admitted = db.execute("SELECT COUNT(*) FROM events WHERE status=200").fetchone()[0]
        if admitted != 60:
            raise ValueError("Quota must admit exactly60authenticated requests including readiness")
        reconcile_requests(audit / "audit.sqlite", rows, model, candidate)
        print(
            "Batas request dan audit lulus; menunggu jendela60detik untuk memeriksa pemulihan.",
            flush=True,
        )
        waited = time.monotonic()
        while time.monotonic() - waited < 61:
            time.sleep(0.5)
        recovered = _workload(name, "recover")
        _require_score(recovered["rows"][0], expected, model)
        reconciled = reconcile_requests(
            audit / "audit.sqlite", rows + recovered["rows"], model, candidate
        )
        if time.monotonic() - started >= 180:
            raise TimeoutError("Local service acceptance exceeded180seconds")
        receipt.update(
            status="PASS_PRIVATE_HTTPS_CAPACITY_BOUNDARY",
            image_id=info["Id"],
            public_source_sha256=source,
            original_bundle_sha256=sha256(bundle),
            synthetic_snapshot_sha256=sha256(snapshot),
            candidate_sha256=candidate,
            workload=measured["workload"],
            process_peak_rss_kib=measured["process_peak_rss_kib"],
            authenticated_quota=60,
            expected_quota_rejections=5,
            unauthenticated_http=401,
            real_wait_seconds=time.monotonic() - waited,
            post_window_score_http=200,
            audit_reconciliation=reconciled,
            self_signed_test_certificate=True,
            original_credential_modified=False,
            operating_slo_verified=False,
            resources={"cpus": 2, "memory_bytes": 2 * 1024**3, "concurrency": [1, 5]},
        )
    except BaseException as error:
        receipt.update(status="FAILED", failure_type=type(error).__name__)
        raise
    finally:
        cleaned = False
        try:
            found = _docker("inspect", name, check=False)
            if found.returncode:
                cleaned = True
            elif (
                json.loads(found.stdout)[0]["Config"]["Labels"].get("creditlens.acceptance")
                == owner
            ):
                logs = _docker("logs", name, check=False)
                log = output / "container.log"
                log.write_text((logs.stdout + logs.stderr).replace(token, "[REDACTED]"))
                log.chmod(0o600)
                cleaned = _docker("rm", "--force", name, check=False).returncode == 0
        except Exception:
            cleaned = False
        receipt["test_owned_containers_removed"] = cleaned
        if not cleaned:
            receipt["status"] = "FAILED_CLEANUP"
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        _write(output / "receipt.json", receipt)
    if receipt["status"] != "PASS_PRIVATE_HTTPS_CAPACITY_BOUNDARY":
        raise ValueError("Bounded service verification or owned cleanup failed")
    return receipt


def main() -> None:
    """Run the fixed synthetic-only service check and report a private receipt location."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    for option in ("bundle", "snapshot", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--confirm-synthetic", required=True, action="store_true")
    parser.add_argument("--assistant-check", action="store_true")
    args = parser.parse_args()
    run_capacity_acceptance(
        args.image,
        args.bundle,
        args.snapshot,
        args.output,
        "assistant_check" if args.assistant_check else "local_command_unverified_identity",
    )
    print("Berhasil: HTTPS bersamaan, batas request, audit dan pemulihan jendela lulus.")
    print("Bukti privat:", args.output / "receipt.json")


if __name__ == "__main__":
    main()
