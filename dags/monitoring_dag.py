"""Daily monitoring DAG for CreditLens.

Runs after the ETL DAG to watch for data drift and model performance
regressions:

    check_data_drift -> check_model_performance

The drift task runs the PSI/KS drift check (with an optional Evidently
HTML report and MLflow logging); the performance task re-evaluates metrics
on the latest mart without gating (reporting only).
"""

from __future__ import annotations

from airflow import DAG
from airflow.operators.bash import BashOperator

from dags.config import DAG_START_DATE, DEFAULT_ARGS, PYTHON_BIN, project_command

DAG_ID = "creditlens_monitoring"

with DAG(
    dag_id=DAG_ID,
    description="Daily data drift and model performance monitoring",
    default_args=DEFAULT_ARGS,
    schedule="0 6 * * *",  # 06:00 daily, after the ETL DAG
    start_date=DAG_START_DATE,
    catchup=False,
    tags=["creditlens", "monitoring", "drift", "evidently"],
) as dag:
    check_data_drift = BashOperator(
        task_id="check_data_drift",
        bash_command=project_command(
            f"{PYTHON_BIN} scripts/run_drift_check.py "
            f"--evidently-out reports/drift.html --track"
        ),
    )

    check_model_performance = BashOperator(
        task_id="check_model_performance",
        bash_command=project_command(f"{PYTHON_BIN} src/ml/evaluate.py --output results/"),
    )

    check_data_drift >> check_model_performance
