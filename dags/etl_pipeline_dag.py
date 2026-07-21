"""Daily ETL orchestration DAG for CreditLens.

Ingests raw sources, runs the dbt staging and mart transformations, tests
the warehouse, and materializes features into the Feast online store:

    ingest_* -> dbt_run_staging -> dbt_run_mart -> dbt_test -> feast_materialize
"""

from __future__ import annotations

from airflow import DAG
from airflow.operators.bash import BashOperator

from dags.config import (
    DAG_START_DATE,
    DBT_BIN,
    DEFAULT_ARGS,
    LENDING_CLUB_CSV,
    PYTHON_BIN,
    project_command,
)

DAG_ID = "creditlens_etl_pipeline"

with DAG(
    dag_id=DAG_ID,
    description="Ingest -> dbt staging/mart -> test -> Feast materialize",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=DAG_START_DATE,
    catchup=False,
    tags=["creditlens", "etl", "dbt", "feast"],
) as dag:
    ingest_lending_club = BashOperator(
        task_id="ingest_lending_club",
        bash_command=project_command(
            f"{PYTHON_BIN} scripts/load_data.py --source lending_club "
            f"--csv-path {LENDING_CLUB_CSV}"
        ),
    )

    ingest_fred = BashOperator(
        task_id="ingest_fred",
        bash_command=project_command(f"{PYTHON_BIN} scripts/load_data.py --source fred"),
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=project_command(f"{DBT_BIN} run --profiles-dir . --select staging"),
    )

    dbt_run_mart = BashOperator(
        task_id="dbt_run_mart",
        bash_command=project_command(f"{DBT_BIN} run --profiles-dir . --select mart"),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=project_command(f"{DBT_BIN} test --profiles-dir ."),
    )

    feast_materialize = BashOperator(
        task_id="feast_materialize",
        bash_command=project_command(f"{PYTHON_BIN} -m src.feature_store.materialize"),
    )

    [ingest_lending_club, ingest_fred] >> dbt_run_staging
    dbt_run_staging >> dbt_run_mart >> dbt_test >> feast_materialize
