"""Score private timestamped monthly research records against the loopback API only."""

from __future__ import annotations

import argparse
import json
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import Any

from src.research.freddie_monthly_adapter import (
    ADAPTER_VERSION,
    DEFAULT_PROTOCOL,
    MonthlySnapshot,
    build_feature_request,
)


def score_snapshot(
    snapshot: MonthlySnapshot, token: str, port: int = 8001, protocol: Path = DEFAULT_PROTOCOL
) -> dict[str, Any]:
    """Send only engineered features to literal loopback without redirect following.

    Args:
        snapshot: Validated private monthly request with supplied availability times.
        token: Private API credential; never included in output.
        port: Unprivileged local API port.
        protocol: Immutable feature protocol.

    Returns:
        Research score and supplied-timestamp checks, not production acceptance.

    Raises:
        ValueError: Invalid port/token/snapshot or API readiness/status/scope mismatch.
        OSError: Local server unreachable or timed out.
    """
    if not 1024 <= port <= 65535 or len(token) < 32:
        raise ValueError("Valid local port and private credential required")
    body = json.dumps(build_feature_request(snapshot, protocol), allow_nan=False)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    responses = []
    connection = HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        for route, payload in (("/ready", None), ("/score", body)):
            connection.request("GET" if payload is None else "POST", route, payload, headers)
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError(f"Local API returned HTTP {response.status} for {route}")
            result = json.loads(response.read(8193))
            if (
                result.get("production_scoring_release") != "HOLD"
                or result.get("public_scoring_authorized") is not False
                or result.get("scope") != "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY"
            ):
                raise ValueError("Unexpected API scope")
            responses.append(result)
    finally:
        connection.close()
    ready, score = responses
    probability = score.get("probability")
    if (
        ready.get("research_ready") is not True
        or ready.get("model_id") != score.get("model_id")
        or type(probability) not in (int, float)
        or not 0 <= probability <= 1
        or score.get("horizon_months") != 3
    ):
        raise ValueError("Inconsistent research readiness/score")
    return {
        **score,
        "adapter_version": ADAPTER_VERSION,
        "ready_http": 200,
        "score_http": 200,
        "as_of_period": snapshot.as_of_period,
        "supplied_availability_checks_passed": True,
        "operational_point_in_time_verified": False,
    }


def main() -> None:
    """Run the private client without printing credentials, loan IDs or validation inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    try:
        for path in (args.snapshot, args.token_file):
            if not path.is_file() or repo in path.resolve().parents or path.stat().st_mode & 0o077:
                raise ValueError("Private owner-only files outside Git required")
        if args.snapshot.stat().st_size > 131072 or args.token_file.stat().st_size > 4096:
            raise ValueError("Private input too large")
        snapshot = MonthlySnapshot.model_validate_json(args.snapshot.read_bytes())
        result = score_snapshot(snapshot, args.token_file.read_text().strip(), args.port)
    except (OSError, HTTPException):
        parser.exit(2, "API lokal belum dapat dihubungi. Jalankan server di terminal pertama.\n")
    except ValueError:
        parser.exit(
            2,
            "Permintaan ditolak: periksa izin file privat, schema, waktu ketersediaan, "
            "token, dan status API. Nilai input/token tidak ditampilkan.\n",
        )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
