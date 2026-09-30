#!/usr/bin/env bash
# Verify one locally available dashboard image; never touches databases or volumes.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/smoke_dashboard_image.sh IMAGE REPORT_JSON" >&2
  exit 2
fi
image_ref="$1"
report_path="$2"
container_id=""
if [[ -e "$report_path" ]]; then
  echo "Report already exists; choose a new report path to preserve evidence." >&2
  exit 2
fi

cleanup() {
  smoke_exit=$?
  if [[ -n "$container_id" ]]; then
    if [[ "$smoke_exit" -ne 0 ]]; then
      docker logs "$container_id" >&2 || true
    fi
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  fi
  exit "$smoke_exit"
}
trap cleanup EXIT

image_id=$(docker image inspect "$image_ref" --format '{{.Id}}')
code_revision=$(git rev-parse HEAD)
container_id=$(docker run --detach --name "creditlens-dashboard-smoke-$$" \
  --label creditlens.purpose=dashboard-smoke \
  --publish 127.0.0.1::8501 "$image_id")
container_endpoint=$(docker port "$container_id" 8501/tcp)
if [[ "$container_endpoint" != 127.0.0.1:* ]]; then
  echo "Dashboard smoke must bind to loopback only." >&2
  exit 1
fi

health_status="starting"
for attempt in {1..30}; do
  health_status=$(docker inspect --format '{{.State.Health.Status}}' "$container_id")
  if [[ "$health_status" == healthy ]]; then
    break
  fi
  if [[ "$health_status" == unhealthy ]]; then
    echo "Dashboard healthcheck failed." >&2
    exit 1
  fi
  sleep 2
done
if [[ "$health_status" != healthy ]]; then
  echo "Dashboard did not become healthy within 60 seconds." >&2
  exit 1
fi

http_status=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --max-time 5 "http://${container_endpoint}/_stcore/health")
if [[ "$http_status" != 200 ]]; then
  echo "Dashboard HTTP healthcheck failed: ${http_status}" >&2
  exit 1
fi

docker exec "$container_id" python -c '
import json
import os
from pathlib import Path
assert os.geteuid() != 0, "Dashboard must run as non-root"
for name in ["data", "models", ".git", ".env", ".local-backups"]:
    assert not (Path("/app") / name).exists(), f"Forbidden image content: {name}"
snapshot = json.loads(Path("/app/docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json").read_text())
assert snapshot["kind"] == "historical_research_aggregates"
assert snapshot["model_release_passed"] is False
assert snapshot["test_consumed"] is True
for cohort in snapshot["cohorts"]:
    assert cohort["eligible"] == cohort["non_adverse"] + cohort["adverse"]
assert snapshot["test"]["average_precision"] < snapshot["test"]["historical_ap_gate"]
'

mkdir -p "$(dirname "$report_path")"
python3 - "$report_path" "$image_id" "$code_revision" <<'PY'
import json
import sys
from pathlib import Path
report_path, image_id, revision = sys.argv[1:]
report = {
    "schema_version": 1,
    "kind": "dashboard_packaging_smoke",
    "status": "passed",
    "image_id": image_id,
    "code_revision": revision,
    "checks": {
        "docker_health": "healthy",
        "http_health": 200,
        "non_root_user": True,
        "forbidden_app_paths_absent": True,
        "historical_counts_reconciled": True,
        "failed_model_gate_disclosed": True,
    },
    "model_release_passed": False,
    "public_deployment_verified": False,
}
Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
print("Dashboard packaging smoke passed; model release remains blocked.")
PY
