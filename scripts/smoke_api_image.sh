#!/usr/bin/env bash
# A live process is insufficient: only verified scoring readiness can pass.
set -euo pipefail
image="${1:?Usage: smoke_api_image.sh IMAGE}"
container_id=""
response="$(mktemp)"
cleanup() {
  if [ -n "$container_id" ]; then docker rm -f "$container_id" >/dev/null; fi
  rm -f "$response"
}
trap cleanup EXIT
container_id="$(docker run --detach --publish 127.0.0.1::8000 "$image")"
port="$(docker port "$container_id" 8000/tcp)"
for attempt in $(seq 1 30); do
  health="$(docker inspect --format '{{.State.Health.Status}}' "$container_id")"
  if [ "$health" = "unhealthy" ]; then
    echo "API readiness healthcheck failed" >&2
    exit 1
  fi
  if curl --fail --silent --max-time 3 "http://$port/ready" > "$response"; then
    if python - "$response" <<'CHECK'
import json
import sys
with open(sys.argv[1]) as handle:
    status = json.load(handle)
valid = (status.get("status") == "ready" and status.get("model_loaded") is True
         and status.get("bundle_verified") is True)
sys.exit(0 if valid else 1)
CHECK
    then
      echo "Verified scoring readiness smoke passed; model quality remains a separate gate"
      exit 0
    fi
    echo "API returned 200 without a verified readiness contract" >&2
    exit 1
  fi
  sleep 2
done
echo "API readiness timed out; no release acceptance" >&2
exit 1
