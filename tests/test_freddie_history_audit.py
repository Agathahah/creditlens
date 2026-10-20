"""Past-only feature and development-only source contracts; no real dataset access."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.research.freddie_history_audit import (
    DEVELOPMENT_HASHES,
    PROTOCOL_SHA,
    Profile,
    past_features,
    profile_history,
    require_development_sources,
)
from src.research.freddie_panel import Observation, month_index

ROOT = Path(__file__).resolve().parents[1]


def observation(period: str, dq: int | None = 0, upb: float = 100.0) -> Observation:
    """Create a synthetic same-loan reporting record."""
    return Observation("fixture", period, upb, dq)


def test_calendar_gaps_and_unknowns_are_not_imputed_to_good_status() -> None:
    """Six rows do not mean six calendar months; incomplete counts remain missing."""
    past = {
        month_index(f"2019{month:02d}"): observation(f"2019{month:02d}")
        for month in (1, 2, 3, 4, 6)
    }
    past[month_index("201904")] = observation("201904", None)
    features = past_features(observation("201907", upb=80), past)
    assert features["observed_months_6"] == 5
    assert features["known_status_months_6"] == 4
    assert features["complete_status_6"] == 0
    assert features["dq_months_6"] is None
    assert features["worst_dq_6"] is None
    assert features["upb_change_ratio_3"] == pytest.approx(-0.2)
    assert features["upb_change_ratio_12"] is None


def test_complete_history_has_known_counts_and_exact_recency() -> None:
    """A previous missed payment stays visible when the current record is current."""
    past = {
        month_index(f"2019{month:02d}"): observation(f"2019{month:02d}", 2 if month == 10 else 0)
        for month in range(1, 13)
    }
    features = past_features(observation("202001"), past)
    assert features["complete_status_12"] == 1
    assert features["worst_dq_6"] == 2
    assert features["dq_months_12"] == 1
    assert features["months_since_known_dq_12"] == 3


def test_future_status_balance_and_as_of_status_are_excluded() -> None:
    """Adding adverse future rows cannot alter any past-history feature."""
    current = observation("202001")
    past = {month_index("201912"): observation("201912", 1)}
    original = past_features(current, past)
    future = {
        **past,
        month_index("202001"): observation("202001", 100, 0),
        month_index("202002"): observation("202002", 100, 0),
    }
    assert past_features(current, future) == original
    profiles: dict[str, Profile] = {}
    assert (
        profile_history(
            [*past.values(), current, observation("202002", 100, 0)],
            {"as_of_start": "202001", "as_of_end": "202001"},
            profiles,
        )
        == 1
    )
    assert profiles["months_since_known_dq_12"].mean == 1


@pytest.mark.parametrize(
    "history",
    [
        [observation("202001"), observation("202001")],
        [observation("202002"), observation("202001")],
        [observation("202001"), Observation("other", "202002", 100, 0)],
    ],
)
def test_bad_identity_or_calendar_is_rejected(history: list[Observation]) -> None:
    """Bad grouping cannot silently create a history feature for the wrong loan."""
    with pytest.raises(ValueError, match="history"):
        profile_history(history, {"as_of_start": "202001", "as_of_end": "202012"}, {})


def test_reservoir_is_bounded_counts_are_exact_and_sample_is_not_exported() -> None:
    """Approximate quantiles never replace exact missing/count/moment evidence."""
    profile = Profile()
    for index in range(5000):
        profile.add(float(index))
    profile.add(None)
    assert len(profile.sample) == 2000
    result = profile.summary()
    assert result["observations"] == 5001
    assert result["mean"] == pytest.approx(2499.5)
    assert result["maximum"] == 4999
    assert result["missing"] == 1
    assert "sample" not in result
    with pytest.raises(ValueError, match="Non-finite"):
        profile.add(float("nan"))


def manifest(tmp_path: Path) -> dict[str, Any]:
    """Build fake private admission for synthetic guarded-read assertions."""
    return {
        "scope": "freddie_mortgage_retrospective_research",
        "admission_scope": "PRIVATE_RETROSPECTIVE_MORTGAGE_RESEARCH_ONLY",
        "source_admitted_for_training": True,
        "protocol_sha256": PROTOCOL_SHA,
        "owner_review": {
            "internal_research_terms_acknowledged": True,
            "retrospective_limitations_acknowledged": True,
        },
        "frozen_test_opened": True,
        "sources": {
            role: {
                "vintage": year,
                "path": str(tmp_path / f"sample_{year}.zip"),
                "sha256": DEVELOPMENT_HASHES[year],
                "bytes": 0,
            }
            for role, year in (("train", 2018), ("validation", 2019))
        },
    }


def test_consumed_test_is_ignored_but_development_identity_is_bound(tmp_path: Path) -> None:
    """Consumed test must not block development audit or be hashed/read by it."""
    source = manifest(tmp_path)
    for item in source["sources"].values():
        Path(item["path"]).touch()
    source["sources"]["frozen_test"] = {"path": "/must-not-read"}
    private = tmp_path / "source.json"
    private.write_text(json.dumps(source))
    protocol = ROOT / "config/research/freddie_experiment_v3.json"

    def mock_hash(path: Path) -> str:
        if path == protocol:
            return PROTOCOL_SHA
        assert path.name in ("sample_2018.zip", "sample_2019.zip")
        return DEVELOPMENT_HASHES[int(path.stem[-4:])]

    with patch("src.research.freddie_history_audit.sha256", side_effect=mock_hash):
        assert require_development_sources(private, protocol) == source
    bad = copy.deepcopy(source)
    bad["sources"]["validation"]["vintage"] = 2020
    private.write_text(json.dumps(bad))
    with patch("src.research.freddie_history_audit.sha256", return_value=PROTOCOL_SHA) as hasher:
        with pytest.raises(ValueError, match="2018/2019"):
            require_development_sources(private, protocol)
        assert hasher.call_count == 1  # Protocol only; no source opened.


def test_changed_terms_or_development_hash_is_rejected_before_source_read(tmp_path: Path) -> None:
    """An arbitrary/new archive cannot inherit historical source acceptance."""
    source = manifest(tmp_path)
    private = tmp_path / "source.json"
    protocol = ROOT / "config/research/freddie_experiment_v3.json"
    source["sources"]["train"]["sha256"] = "unexpected"
    private.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="2018/2019"):
        require_development_sources(private, protocol)
    source = manifest(tmp_path)
    source["owner_review"]["internal_research_terms_acknowledged"] = False
    private.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="Admitted"):
        require_development_sources(private, protocol)


def test_cli_rejects_repository_output_before_source_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hidden worker mode must retain the same private-output boundary as parent mode."""
    from src.research.freddie_history_audit import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "audit",
            "--manifest",
            "/not-readable.json",
            "--protocol",
            "/not-readable-protocol.json",
            "--output",
            str(ROOT / "audit-should-not-be-created"),
            "--worker",
        ],
    )
    with pytest.raises(ValueError, match="outside Git"):
        main()
    assert not (ROOT / "audit-should-not-be-created").exists()


def test_worker_exports_only_aggregates_and_preserves_previous_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real aggregation over synthetic histories exports neither loan IDs nor sample values."""
    import hashlib
    from collections.abc import Iterator

    from src.research.freddie_history_audit import audit_worker

    source = manifest(tmp_path)
    source["sources"]["frozen_test"] = {"path": "/never-open-test"}
    monkeypatch.setattr(
        "src.research.freddie_history_audit.require_development_sources", lambda *_: source
    )
    protocol = ROOT / "config/research/freddie_experiment_v3.json"
    salt = json.loads(protocol.read_text())["split"]["calibration"]["loan_partition"]["salt"]
    identities: dict[int, str] = {}
    for index in range(20):
        identity = f"private-fixture-loan-{index}"
        bucket = int(hashlib.sha256((salt + ":" + identity).encode()).hexdigest(), 16) % 2
        identities[bucket] = identity
    assert set(identities) == {0, 1}

    def histories(archive: Path, vintage: int) -> Iterator[list[Observation]]:
        assert archive.name == f"sample_{vintage}.zip"
        assert vintage in (2018, 2019)
        if vintage == 2018:
            yield [Observation("private-fixture-train", "201901", 100, 0)]
        else:
            for identity in identities.values():
                yield [Observation(identity, period, 100, 0) for period in ("202101", "202204")]

    monkeypatch.setattr("src.research.freddie_history_audit.iter_histories", histories)
    output = tmp_path / "private"
    output.mkdir()
    audit_worker(tmp_path / "unused-manifest.json", protocol, output)
    path = output / "history_profile.json"
    report = json.loads(path.read_text())
    assert all(role["eligible_observations"] == 1 for role in report["roles"].values())
    assert report["model_fit_performed"] is False
    assert report["test_source_accessed"] is False
    assert "private-fixture" not in path.read_text()
    assert "sample" not in report["roles"]["train"]["features"]["dq_months_12"]
    assert path.stat().st_mode & 0o777 == 0o600
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        audit_worker(tmp_path / "unused-manifest.json", protocol, output)
    assert path.read_bytes() == original
