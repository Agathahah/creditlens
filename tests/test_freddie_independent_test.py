"""One-shot frozen-test ledger and prediction-only boundaries without private source access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.research.freddie_independent_test import (
    authorize_test_access,
    record_consumption,
    score_without_fit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_consumption_is_private_and_cannot_be_reset_by_retry(tmp_path: Path) -> None:
    """Failure after first access does not make the test available for another attempt."""
    marker = tmp_path / "consumed.json"
    contract = {"candidate_sha256": "own-fixture", "test_source_sha256": "opaque-fixture"}
    record_consumption(marker, contract)
    original = marker.read_bytes()
    assert json.loads(original)["consumed"] is True
    assert marker.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        record_consumption(marker, contract)
    assert marker.read_bytes() == original


def test_changed_validation_identity_is_rejected_before_any_test_opener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even the exact execution contract cannot admit changed candidate evaluation evidence."""
    execution = ROOT / "config/research/freddie_independent_test_v3.json"
    contract = json.loads(execution.read_text())
    manifest = tmp_path / "source.json"
    manifest.write_text("{}")
    run = tmp_path / "run"
    run.mkdir()
    (run / "validation_report.json").write_text("{}")
    monkeypatch.setattr(
        "src.research.freddie_independent_test.require_training_admission",
        lambda *args: {"sources": {"frozen_test": {"sha256": contract["test_source_sha256"]}}},
    )
    with pytest.raises(ValueError, match="prerequisite"):
        authorize_test_access(
            run, ROOT / "config/research/freddie_experiment_v3.json", execution, manifest
        )
    assert not (tmp_path / "frozen_test_consumed_2020.json").exists()


@pytest.mark.parametrize("bad_probability", [False, True])
def test_locked_scoring_never_fits_or_mutates_the_candidate(bad_probability: bool) -> None:
    """A candidate needing fit is unusable; only finite already-fitted predictions are accepted."""

    class FrozenFixture:
        def fit(self, *args: Any) -> Any:
            raise AssertionError("Test must never fit")

        def predict_proba(self, features: pd.DataFrame) -> np.ndarray[Any, Any]:
            probabilities = np.array([0.01, 0.2])
            if bad_probability:
                probabilities[0] = np.nan
            return np.column_stack((1 - probabilities, probabilities))

    frame = pd.DataFrame({"domain_value": [1, 2]})
    if bad_probability:
        with pytest.raises(ValueError, match="probabilities"):
            score_without_fit(FrozenFixture(), frame)
    else:
        np.testing.assert_array_equal(score_without_fit(FrozenFixture(), frame), [0.01, 0.2])


def test_synthetic_independent_executor_audits_panel_without_refitting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consume synthetic ZIP, load own fixture and reject its fixed constant score on test."""
    import sqlite3
    import zipfile

    import joblib
    from sklearn.dummy import DummyClassifier

    from src.research.freddie_independent_test import independent_worker
    from src.research.freddie_preflight import sha256

    archive = tmp_path / "sample_2020.zip"
    origination, performance = [], []
    for i in range(80):
        key = f"synthetic-2020-{i}"
        row = [""] * 31
        row[0], row[8], row[9], row[11], row[19] = "700", "80", "30", "70", key
        origination.append("|".join(row))
        for month in ("202307", "202308", "202309", "202310"):
            row = [""] * 35
            row[0], row[1], row[2], row[3], row[10] = (
                key,
                month,
                "10000",
                ("3" if i < 40 and month >= "202309" else "0"),
                "4.0",
            )
            performance.append("|".join(row))
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sample_orig_2020.txt", "\n".join(origination) + "\n")
        handle.writestr("sample_perf_2020.txt", "\n".join(performance) + "\n")
    run = tmp_path / "validation"
    run.mkdir()
    model = DummyClassifier(strategy="prior").fit(np.ones((100, 10)), np.r_[1, np.zeros(99)])
    weights = run / "candidate_pipeline.joblib"
    joblib.dump(model, weights)
    contract = {
        "candidate_sha256": sha256(weights),
        "test_source_sha256": sha256(archive),
        "scope": "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY",
    }
    record_consumption(tmp_path / "frozen_test_consumed_2020.json", contract)
    (run / "validation_report.json").write_text(
        json.dumps(
            {
                "selected_candidate": "synthetic_constant_fixture",
                "train_constant_prevalence": 0.01,
                "calibration_constant_prevalence": 0.01,
            }
        )
    )
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps({"sources": {"frozen_test": {"path": str(archive)}}}))
    prior = tmp_path / "earlier.sqlite"
    with sqlite3.connect(prior) as db:
        db.execute("CREATE TABLE loan_month(loan_id TEXT)")
        db.execute("INSERT INTO loan_month VALUES ('synthetic-older-loan')")
    monkeypatch.setattr(
        "src.research.freddie_independent_test.authorize_test_access", lambda *args: contract
    )

    def cannot_fit(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Independent executor must never fit")

    monkeypatch.setattr(DummyClassifier, "fit", cannot_fit)
    output = tmp_path / "test_result"
    output.mkdir()
    independent_worker(
        run,
        ROOT / "config/research/freddie_experiment_v3.json",
        tmp_path / "execution.json",
        manifest,
        output,
        prior,
        prior,
    )
    report = json.loads((output / "test_report.json").read_text())
    assert report["test_decision"] == "REJECT_TEST"
    assert report["frozen_test_opened"] is True
    assert report["test_vintage_consumed"] == 2020
    assert report["loan_identity_overlap"] == 0
    assert report["scoring_release"] == "HOLD"
    assert sha256(weights) == contract["candidate_sha256"]
