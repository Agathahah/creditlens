"""Daily monitoring DAG for CreditLens.

Runs after the ETL DAG to watch for data drift and model performance
regressions:

    check_data_drift -> check_model_performance

The drift task is a placeholder for the upcoming Evidently AI integration;
the performance task re-evaluates metrics on the latest mart without
gating (reporting only).
"""

from __future__ import annotations

import logging

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from dags.config import DAG_START_DATE, DEFAULT_ARGS, PYTHON_BIN, project_command

DAG_ID = "creditlens_monitoring"

logger = logging.getLogger("creditlens.monitoring")


def check_data_drift() -> str:
    """Placeholder drift check pending Evidently AI integration.

    Returns:
        A status string recorded in the task logs and XCom.
    """
    logger.info("Data drift check placeholder — Evidently AI integration pending.")
    return "drift_check_placeholder"


with DAG(
    dag_id=DAG_ID,
    description="Daily data drift and model performance monitoring",
    default_args=DEFAULT_ARGS,
    schedule="0 6 * * *",  # 06:00 daily, after the ETL DAG
    start_date=DAG_START_DATE,
    catchup=False,
    tags=["creditlens", "monitoring", "drift"],
) as dag:
    drift_task = PythonOperator(
        task_id="check_data_drift",
        python_callable=check_data_drift,
    )

    performance_task = BashOperator(
        task_id="check_model_performance",
        bash_command=project_command(f"{PYTHON_BIN} src/ml/evaluate.py --output results/"),
    )

    drift_task >> performance_task
