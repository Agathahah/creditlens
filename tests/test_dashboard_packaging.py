"""Verify failed dashboard health cannot produce a successful packaging report."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unhealthy_dashboard_fails_and_removes_only_its_container(
    tmp_path: Path,
) -> None:
    """An unhealthy image must fail before HTTP probing or success reporting.

    Args:
        tmp_path: Isolated directory holding controlled command fixtures.
    """
    commands = tmp_path / "commands"
    commands.mkdir()
    calls = tmp_path / "docker_calls.txt"
    docker = commands / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$SMOKE_TEST_CALLS"\n'
        'case "$1" in\n'
        '  image) echo "sha256:controlled-fixture" ;;\n'
        '  run) echo "controlled-container" ;;\n'
        '  port) echo "127.0.0.1:54321" ;;\n'
        '  inspect) echo "unhealthy" ;;\n'
        "  logs|rm) exit 0 ;;\n"
        "  *) exit 97 ;;\n"
        "esac\n"
    )
    docker.chmod(0o755)
    curl = commands / "curl"
    curl.write_text("#!/usr/bin/env bash\nexit 98\n")
    curl.chmod(0o755)
    git = commands / "git"
    git.write_text('#!/usr/bin/env bash\necho "1111111111111111111111111111111111111111"\n')
    git.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(commands) + os.pathsep + env["PATH"]
    env["SMOKE_TEST_CALLS"] = str(calls)
    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/smoke_dashboard_image.sh"),
            "fixture-image",
            str(report),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert "healthcheck failed" in result.stderr
    assert not report.exists()
    operations = calls.read_text()
    assert "--publish 127.0.0.1::8501" in operations
    assert "rm -f controlled-container" in operations
    assert "prune" not in operations
    assert "volume" not in operations
