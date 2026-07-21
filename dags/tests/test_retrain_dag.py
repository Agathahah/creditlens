"""Structural tests for the model retraining DAG."""

from __future__ import annotations

from typing import Any

RETRAIN_DAG_ID = "creditlens_model_retrain"


def test_retrain_dag_tasks(dagbag: Any) -> None:
    """Retrain DAG must expose the four expected tasks."""
    dag = dagbag.get_dag(RETRAIN_DAG_ID)
    assert dag is not None
    assert set(dag.task_ids) == {
        "retrain_xgboost",
        "retrain_lightgbm",
        "evaluate_model",
        "fairness_audit",
    }


def test_retrain_dag_dependencies(dagbag: Any) -> None:
    """Both retrain tasks must gate evaluation, which gates the audit."""
    dag = dagbag.get_dag(RETRAIN_DAG_ID)
    evaluate = dag.get_task("evaluate_model")
    assert set(evaluate.upstream_task_ids) == {"retrain_xgboost", "retrain_lightgbm"}
    assert dag.get_task("fairness_audit").upstream_task_ids == {"evaluate_model"}


def test_retrain_dag_weekly_schedule(dagbag: Any) -> None:
    """Retrain DAG must run weekly on Sunday with catchup disabled."""
    dag = dagbag.get_dag(RETRAIN_DAG_ID)
    assert dag.schedule_interval == "0 3 * * 0"
    assert dag.catchup is False


def test_evaluate_task_enforces_pr_auc_gate(dagbag: Any) -> None:
    """The evaluation task must invoke the PR-AUC threshold check."""
    dag = dagbag.get_dag(RETRAIN_DAG_ID)
    command = dag.get_task("evaluate_model").bash_command
    assert "--threshold-check" in command
    assert "--pr-auc-min" in command
