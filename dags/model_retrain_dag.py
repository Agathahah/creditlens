"""Weekly model retraining DAG for CreditLens.

Retrains the candidate models, gates them on the PR-AUC regression check,
and runs a fairness audit before a model can be promoted:

    retrain_* -> evaluate_model -> fairness_audit

Scheduled every Sunday so it runs on a fresh mart produced by the daily
ETL DAG.
"""

from __future__ import annotations

from airflow import DAG
from airflow.operators.bash import BashOperator

from dags.config import (
    DAG_START_DATE,
    DEFAULT_ARGS,
    PR_AUC_MIN,
    PYTHON_BIN,
    project_command,
)

DAG_ID = "creditlens_model_retrain"

with DAG(
    dag_id=DAG_ID,
    description="Retrain -> evaluate (PR-AUC gate) -> fairness audit",
    default_args=DEFAULT_ARGS,
    schedule="0 3 * * 0",  # 03:00 every Sunday
    start_date=DAG_START_DATE,
    catchup=False,
    tags=["creditlens", "ml", "retrain", "fairness"],
) as dag:
    retrain_xgboost = BashOperator(
        task_id="retrain_xgboost",
        bash_command=project_command(f"{PYTHON_BIN} src/ml/train.py --model xgboost --track"),
    )

    retrain_lightgbm = BashOperator(
        task_id="retrain_lightgbm",
        bash_command=project_command(f"{PYTHON_BIN} src/ml/train.py --model lightgbm --track"),
    )

    evaluate_model = BashOperator(
        task_id="evaluate_model",
        bash_command=project_command(
            f"{PYTHON_BIN} src/ml/evaluate.py --threshold-check --pr-auc-min {PR_AUC_MIN}"
        ),
    )

    fairness_audit = BashOperator(
        task_id="fairness_audit",
        bash_command=project_command(f"{PYTHON_BIN} scripts/run_fairness_audit.py"),
    )

    [retrain_xgboost, retrain_lightgbm] >> evaluate_model >> fairness_audit
