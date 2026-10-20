"""Negative image-smoke contracts with controlled commands, not real model results."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "body,expected",
    [
        ('{"status":"ready","model_loaded":true,"bundle_verified":true}', 0),
        ('{"status":"ok","model_loaded":false,"bundle_verified":false}', 1),
    ],
)
def test_api_smoke_requires_verified_ready_and_cleans_container(
    tmp_path: Path,
    body: str,
    expected: int,
) -> None:
    """A HTTP-200 liveness response must not pass the image release smoke."""
    commands = tmp_path / "commands"
    commands.mkdir()
    calls = tmp_path / "calls"
    docker = commands / "docker"
    docker.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$SMOKE_TEST_CALLS"\n'
        'case "$1" in\n run) echo fixture-container ;;\n'
        " port) echo 127.0.0.1:12345 ;;\n inspect) echo healthy ;;\n"
        " rm) exit 0 ;;\n *) exit 98 ;;\nesac\n"
    )
    curl = commands / "curl"
    curl.write_text(
        '#!/usr/bin/env bash\nprintf "curl %s\\n" "$*" >> "$SMOKE_TEST_CALLS"\n'
        'printf "%s" "$SMOKE_TEST_BODY"\n'
    )
    for path in (docker, curl):
        path.chmod(0o755)
    env = dict(os.environ, SMOKE_TEST_CALLS=str(calls), SMOKE_TEST_BODY=body)
    env["PATH"] = str(commands) + os.pathsep + env["PATH"]
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/smoke_api_image.sh"), "fixture-image"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected
    assert "--publish 127.0.0.1::8000" in calls.read_text()
    assert "rm -f fixture-container" in calls.read_text()
    assert "http://127.0.0.1:12345/ready" in calls.read_text()
