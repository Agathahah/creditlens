"""Shared configuration for CreditLens Airflow DAGs.

Centralizes the project root, interpreter/tool paths, and default task
arguments so the individual DAG modules stay small and consistent. Paths
are overridable via environment variables so the same DAGs run inside the
Airflow container (docker-compose) and on a developer machine.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

# Project root inside the Airflow worker; the compose file mounts the repo here.
PROJECT_ROOT: str = os.environ.get("CREDITLENS_PROJECT_ROOT", "/opt/creditlens")

# Executables — default to the project virtualenv, matching the Makefile convention.
PYTHON_BIN: str = os.environ.get("CREDITLENS_PYTHON", ".venv/bin/python")
DBT_BIN: str = os.environ.get("CREDITLENS_DBT", ".venv/bin/dbt")

# Path to the Lending Club CSV consumed by the ingestion task.
LENDING_CLUB_CSV: str = os.environ.get("CREDITLENS_LC_CSV", "data/raw/lending_club_loans.csv")

# PR-AUC regression gate for the retraining DAG (mirrors CI eval-gate).
PR_AUC_MIN: str = os.environ.get("CREDITLENS_PR_AUC_MIN", "0.25")

DEFAULT_ARGS: dict[str, Any] = {
    "owner": "creditlens",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Fixed start date keeps DAG runs deterministic; catchup is disabled per DAG.
DAG_START_DATE: datetime = datetime(2026, 1, 1)


def project_command(command: str) -> str:
    """Wrap a shell command so it runs from the project root.

    Args:
        command: Shell command to execute relative to the project root.

    Returns:
        Command string prefixed with a ``cd`` into the project root.
    """
    return f"cd {PROJECT_ROOT} && {command}"
