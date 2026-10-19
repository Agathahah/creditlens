"""Hash exactly the public source, protocol and build inputs for the research API image."""

from __future__ import annotations

import hashlib
from pathlib import Path


def source_tree_sha256(repo: Path) -> str:
    """Bind public build inputs without reading private artifacts or source datasets.

    Args:
        repo: Repository root containing the research source and Docker build files.

    Returns:
        SHA-256 over ordered relative filenames and their exact bytes.
    """
    paths = sorted((repo / "src/research").glob("*.py")) + [
        repo / "src/__init__.py",
        repo / "infra/docker/requirements.research-api.txt",
        repo / "infra/docker/Dockerfile.research-api",
        repo / "config/research/freddie_experiment_v4.json",
        repo / "config/research/freddie_independent_test_v4.json",
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(repo)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


if __name__ == "__main__":
    print(source_tree_sha256(Path(__file__).resolve().parents[1]))
