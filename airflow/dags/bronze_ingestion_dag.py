"""
bronze_ingestion_dag — ingest all 7 tables → Bronze Delta/S3, then GX, then trigger Silver.

Schedule: @daily (staging/prod) | None (dev — manual trigger)
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

ENV = os.getenv("ENV", "dev")

default_args = {
    "owner": "raja-luqman",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

TABLES = [
    "application_train",
    "bureau",
    "bureau_balance",
    "previous_application",
    "installments_payments",
    "POS_CASH_balance",
    "credit_card_balance",
]


def _download_kaggle(**ctx):
    from bronze.download_dataset import load_env, validate_kaggle_credentials, download_competition_dataset, sample_dev_data
    load_env(ENV)
    validate_kaggle_credentials()
    data_dir = download_competition_dataset()
    if ENV == "dev":
        sample_dev_data(data_dir, rows=1000)


def _ingest_table(table: str, **ctx):
    from bronze.ingest_bronze import run
    ingestion_date = ctx["ds"]
    result = run(table=table, env=ENV, ingestion_date=ingestion_date)
    if result["rows_written"] == 0:
        raise RuntimeError(f"No rows written for {table} — check source data")


def _run_gx_bronze(**ctx):
    from gx.run_bronze_suite import run
    run(env=ENV, ingestion_date=ctx["ds"])


def _slack_fail(context):
    SlackWebhookOperator(
        task_id="slack_fail",
        slack_webhook_conn_id="slack_webhook",
        message=f"❌ *bronze_ingestion_dag* FAILED | task: {context['task_instance'].task_id} | {context['ds']}",
    ).execute(context)


with DAG(
    dag_id="bronze_ingestion_dag",
    default_args={**default_args, "on_failure_callback": _slack_fail},
    schedule_interval="@daily" if ENV != "dev" else None,
    catchup=False,
    tags=["bronze", "ingestion"],
) as dag:

    download = PythonOperator(
        task_id="download_kaggle_data",
        python_callable=_download_kaggle,
    )

    ingest_tasks = [
        PythonOperator(
            task_id=f"ingest_{table}_bronze",
            python_callable=_ingest_table,
            op_kwargs={"table": table},
        )
        for table in TABLES
    ]

    gx_bronze = PythonOperator(
        task_id="run_gx_bronze_suite",
        python_callable=_run_gx_bronze,
    )

    trigger_silver = TriggerDagRunOperator(
        task_id="trigger_silver_dag",
        trigger_dag_id="silver_transforms_dag",
        wait_for_completion=False,
    )

    download >> ingest_tasks >> gx_bronze >> trigger_silver
