#!/usr/bin/env bash
# Software-only image check. No private model, credential or source dataset is available.
set -euo pipefail
if [[ $# -ne 2 || -e "$2" ]]; then
  echo "Usage: bash scripts/smoke_research_image.sh IMAGE NEW_REPORT_JSON" >&2
  exit 2
fi
research_image_id=$(docker image inspect "$1" --format '{{.Id}}')
research_source_sha=$(python3 scripts/research_image_source_hash.py)
research_image_sha=$(docker image inspect "$research_image_id" --format '{{index .Config.Labels "org.creditlens.source-tree-sha256"}}')
if [[ "$research_source_sha" != "$research_image_sha" ]]; then
  echo "Image public source identity mismatch." >&2
  exit 1
fi
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --entrypoint python "$research_image_id" -c '
import importlib.metadata
import os
from pathlib import Path
from src.research.freddie_shadow_api import verify_bundle
assert os.geteuid() != 0
assert not Path("/run/research").exists()
for path in Path("/app").rglob("*"):
    assert path.name not in (".git", ".env", "api_token.txt")
    assert path.suffix not in (".joblib", ".zip", ".csv", ".gz", ".sqlite")
for row in Path("/app/requirements.txt").read_text().splitlines():
    if row and not row.startswith("#"):
        name, expected = row.split("==")
        assert importlib.metadata.version(name) == expected
try:
    verify_bundle(Path("/run/research/missing-bundle.json"))
except FileNotFoundError:
    pass
else:
    raise AssertionError("Missing bundle must not become a verified research model")
'
python3 - "$2" "$research_image_id" "$research_source_sha" <<'PY'
import json
import subprocess
import sys
from pathlib import Path
report, image, source = sys.argv[1:]
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
Path(report).write_text(json.dumps({
    "status": "PASS_SOFTWARE_IMAGE_ONLY", "image_id": image,
    "public_source_sha256": source, "checkout_revision": revision,
    "private_artifacts_in_image": False, "real_model_loaded": False,
    "production_scoring_release": "HOLD"
}, indent=2) + "\n")
PY
