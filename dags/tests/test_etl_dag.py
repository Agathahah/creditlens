"""Structural tests for the ETL and monitoring DAGs."""

from __future__ import annotations

from typing import Any

ETL_DAG_ID = "creditlens_etl_pipeline"
MONITORING_DAG_ID = "creditlens_monitoring"


def test_no_import_errors(dagbag: Any) -> None:
    """The DagBag must load every DAG without import errors."""
    assert dagbag.import_errors == {}


def test_etl_dag_tasks(dagbag: Any) -> None:
    """ETL DAG must expose exactly the six expected tasks."""
    dag = dagbag.get_dag(ETL_DAG_ID)
    assert dag is not None
    assert set(dag.task_ids) == {
        "ingest_lending_club",
        "ingest_fred",
        "dbt_run_staging",
        "dbt_run_mart",
        "dbt_test",
        "feast_materialize",
    }


def test_etl_dag_dependencies(dagbag: Any) -> None:
    """ETL DAG must wire ingest -> staging -> mart -> test -> materialize."""
    dag = dagbag.get_dag(ETL_DAG_ID)
    staging = dag.get_task("dbt_run_staging")
    assert set(staging.upstream_task_ids) == {"ingest_lending_club", "ingest_fred"}
    assert dag.get_task("dbt_run_mart").upstream_task_ids == {"dbt_run_staging"}
    assert dag.get_task("dbt_test").upstream_task_ids == {"dbt_run_mart"}
    assert dag.get_task("feast_materialize").upstream_task_ids == {"dbt_test"}


def test_etl_dag_schedule_and_catchup(dagbag: Any) -> None:
    """ETL DAG must run daily with catchup disabled."""
    dag = dagbag.get_dag(ETL_DAG_ID)
    assert dag.schedule_interval == "@daily"
    assert dag.catchup is False


def test_monitoring_dag_structure(dagbag: Any) -> None:
    """Monitoring DAG must chain drift check before performance check."""
    dag = dagbag.get_dag(MONITORING_DAG_ID)
    assert dag is not None
    assert set(dag.task_ids) == {"check_data_drift", "check_model_performance"}
    assert dag.get_task("check_model_performance").upstream_task_ids == {"check_data_drift"}
