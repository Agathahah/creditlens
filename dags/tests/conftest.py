"""Pytest fixtures for Airflow DAG structure tests.

Provides a DagBag loaded from the ``dags`` folder against a throwaway
AIRFLOW_HOME, and skips the whole module when Airflow is not installed
(e.g. the lightweight CI env — Airflow runs in its own container).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("airflow")

DAGS_FOLDER = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dagbag(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Load all CreditLens DAGs into a DagBag for structural assertions."""
    airflow_home = tmp_path_factory.mktemp("airflow_home")
    os.environ.setdefault("AIRFLOW_HOME", str(airflow_home))
    os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "False"
    os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = str(DAGS_FOLDER)

    from airflow.models import DagBag

    return DagBag(dag_folder=str(DAGS_FOLDER), include_examples=False)
