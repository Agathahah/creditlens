"""Timestamp selection, batch-serving feature parity and loopback client failure contracts."""

from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from src.research.freddie_history_train import collect_development
from src.research.freddie_monthly_adapter import (
    DEFAULT_PROTOCOL,
    MonthlySnapshot,
    build_feature_request,
)
from src.research.freddie_monthly_client import score_snapshot


def snapshot_data() -> dict[str, Any]:
    """Construct a synthetic active loan and its exact prior calendar history."""
    records = []
    for lag in range(12, -1, -1):
        index = 2023 * 12 + 11 - lag
        year, zero_month = divmod(index, 12)
        available_year, available_month = divmod(index + 1, 12)
        records.append(
            {
                "loan_key": "synthetic-only",
                "period": f"{year:04}{zero_month + 1:02}",
                "available_at": f"{available_year:04}-{available_month + 1:02}-05T00:00:00Z",
                "upb": 100000 + lag * 1000,
                "dq": 2 if lag == 4 else (1 if lag == 1 else 0),
                "loan_age": 36 - lag,
                "remaining_months": 324 + lag,
                "interest_rate": 6.0,
            }
        )
    return {
        "loan_key": "synthetic-only",
        "as_of_period": "202312",
        "prediction_time": "2024-01-15T00:00:00Z",
        "origination": {
            "available_at": "2022-01-01T00:00:00Z",
            "credit_score": 700,
            "orig_cltv": 80,
            "orig_dti": 35,
            "orig_ltv": 80,
        },
        "records": records,
    }


def build(data: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    """Validate the wire JSON representation before applying the adapter."""
    return build_feature_request(MonthlySnapshot.model_validate_json(json.dumps(data)))


def test_raw_records_match_training_collector_exactly(tmp_path: Path) -> None:
    """The adapter and existing batch collector must produce identical float32 columns."""
    data = snapshot_data()
    config = json.loads(DEFAULT_PROTOCOL.read_text())
    orig = [""] * 31
    orig[0], orig[8], orig[9], orig[11], orig[19] = "700", "80", "35", "80", data["loan_key"]
    rows = []
    records = copy.deepcopy(data["records"])
    for period in ("202401", "202402", "202403", "202603"):
        records.append({**records[-1], "period": period, "dq": 0})
    for record in records:
        row = [""] * 35
        row[:6] = [
            data["loan_key"],
            record["period"],
            str(record["upb"]),
            str(record["dq"]),
            str(record["loan_age"]),
            str(record["remaining_months"]),
        ]
        row[10] = str(record["interest_rate"])
        rows.append("|".join(row))
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as target:
        target.writestr("sample_orig_2021.txt", "|".join(orig) + "\n")
        target.writestr("sample_perf_2021.txt", "\n".join(rows) + "\n")
    cohort = collect_development(
        archive,
        2021,
        {
            "validation": {
                "vintage": 2021,
                "as_of_start": "202312",
                "as_of_end": "202312",
                "last_outcome": "202403",
            }
        },
        config,
    )["validation"]
    features = build(data)["features"]
    assert list(features) == config["features"]
    np.testing.assert_array_equal(
        np.array([list(features.values())], dtype=np.float32), cohort.features.to_numpy()
    )


def test_future_records_and_late_corrections_cannot_change_features() -> None:
    data = snapshot_data()
    before = build(data)
    late = {**data["records"][-2], "available_at": "2024-02-01T00:00:00Z", "dq": 99}
    future = {**late, "period": "202401", "available_at": "2024-02-05T00:00:00Z"}
    data["records"].extend([late, future])
    assert build(data) == before


def test_latest_available_correction_selected_independent_of_input_order() -> None:
    data = snapshot_data()
    data["records"].append({**data["records"][-2], "available_at": "2024-01-10T00:00:00Z", "dq": 2})
    assert build(data)["features"]["prior_dq_1"] == 2
    data["records"].reverse()
    assert build(data)["features"]["prior_dq_1"] == 2


@pytest.mark.parametrize("unknown", [False, True])
def test_gaps_and_unknown_status_remain_explicitly_missing(unknown: bool) -> None:
    data = snapshot_data()
    if unknown:
        data["records"][-2]["dq"] = None
    else:
        del data["records"][-2]
    features = build(data)["features"]
    assert features["prior_dq_1"] is None
    assert features["complete_status_6"] == 0
    assert features["worst_dq_6"] is None
    assert features["dq_months_12"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "mixed",
        "duplicate",
        "unavailable_current",
        "ineligible",
        "terminal",
        "early_prediction",
        "early_availability",
        "late_origination",
        "naive_time",
        "invalid_period",
        "bool",
        "nan",
        "outcome",
        "bad_static",
    ],
)
def test_invalid_or_ineligible_snapshots_fail_closed(mutation: str) -> None:
    data = snapshot_data()
    record = data["records"][-1]
    if mutation == "mixed":
        record["loan_key"] = "other"
    elif mutation == "duplicate":
        data["records"].append(copy.deepcopy(record))
    elif mutation == "unavailable_current":
        record["available_at"] = "2024-02-01T00:00:00Z"
    elif mutation == "ineligible":
        record["dq"] = 1
    elif mutation == "terminal":
        record["zero_balance_code"] = "01"
    elif mutation == "early_prediction":
        data["prediction_time"] = "2023-12-15T00:00:00Z"
    elif mutation == "early_availability":
        record["available_at"] = "2023-12-01T00:00:00Z"
    elif mutation == "late_origination":
        data["origination"]["available_at"] = "2024-02-01T00:00:00Z"
    elif mutation == "naive_time":
        data["prediction_time"] = "2024-01-15T00:00:00"
    elif mutation == "invalid_period":
        record["period"] = "202313"
    elif mutation == "bool":
        record["dq"] = True
    elif mutation == "nan":
        record["upb"] = float("nan")
    elif mutation == "outcome":
        record["future_label"] = 1
    else:
        data["origination"]["orig_dti"] = 80
    with pytest.raises(ValueError):
        build(data)


def test_origination_sentinels_follow_training_missing_rules() -> None:
    data = snapshot_data()
    data["origination"]["credit_score"] = 9999
    data["origination"]["orig_dti"] = 999
    features = build(data)["features"]
    assert features["credit_score"] is None and features["orig_dti"] is None


def test_modified_protocol_rejected_before_feature_use(tmp_path: Path) -> None:
    path = tmp_path / "changed.json"
    path.write_text(DEFAULT_PROTOCOL.read_text() + "\n")
    with pytest.raises(ValueError, match="Locked v4"):
        build_feature_request(
            MonthlySnapshot.model_validate_json(json.dumps(snapshot_data())), path
        )


@pytest.mark.parametrize("status", [301, 401, 422, 429, 503])
def test_client_does_not_follow_redirects_or_ignore_api_failure(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls: list[tuple[str, str]] = []

    class Response:
        def __init__(self) -> None:
            self.status = status

    class Connection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert host == "127.0.0.1" and port == 8001 and timeout == 10

        def request(self, method: str, path: str, body: Any, headers: Any) -> None:
            calls.append((method, path))

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr("src.research.freddie_monthly_client.HTTPConnection", Connection)
    with pytest.raises(ValueError, match=f"HTTP {status}"):
        score_snapshot(
            MonthlySnapshot.model_validate_json(json.dumps(snapshot_data())), "synthetic" * 4
        )
    assert calls == [("GET", "/ready")]


@pytest.mark.parametrize("mutation", ["none", "model_changed", "production", "nonfinite"])
def test_client_checks_response_identity_and_sends_only_features(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    calls: list[tuple[str, str, Any]] = []
    base: dict[str, Any] = {
        "scope": "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY",
        "production_scoring_release": "HOLD",
        "public_scoring_authorized": False,
        "model_id": "fixture",
    }
    replies = [
        {**base, "research_ready": True},
        {**base, "probability": 0.125, "horizon_months": 3},
    ]
    if mutation == "model_changed":
        replies[1]["model_id"] = "changed"
    elif mutation == "production":
        replies[1]["production_scoring_release"] = "READY"
    elif mutation == "nonfinite":
        replies[1]["probability"] = float("nan")

    class Response:
        status = 200

        def read(self, limit: int) -> bytes:
            return json.dumps(replies.pop(0)).encode()

    class Connection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert host == "127.0.0.1"

        def request(self, method: str, path: str, body: Any, headers: Any) -> None:
            calls.append((method, path, body))

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr("src.research.freddie_monthly_client.HTTPConnection", Connection)
    snapshot = MonthlySnapshot.model_validate_json(json.dumps(snapshot_data()))
    if mutation != "none":
        with pytest.raises(ValueError):
            score_snapshot(snapshot, "synthetic" * 4)
    else:
        result = score_snapshot(snapshot, "synthetic" * 4)
        assert result["probability"] == 0.125
        assert result["operational_point_in_time_verified"] is False
        assert "loan_key" not in result
        sent = json.loads(calls[1][2])
        assert set(sent) == {"features"} and len(sent["features"]) == 19
        assert "loan_key" not in sent["features"]
        assert calls[0] == ("GET", "/ready", None)
