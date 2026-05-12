"""
silver_transforms_dag — trigger 5 Glue jobs → GX silver suite → trigger Gold.

Schedule: None (triggered by bronze_ingestion_dag via TriggerDagRunOperator)
Dependency: glue_silver_bureau depends on glue_silver_application (RI check in GX).
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

ENV = os.getenv("ENV", "dev")
BUCKET = os.getenv(f"S3_BUCKET_{ENV.upper()}", f"home-credit-risk-{ENV}")

default_args = {
    "owner": "raja-luqman",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

GLUE_ARGS = {
    "--env": ENV,
    "--date": "{{ ds }}",
    "--bucket": BUCKET,
}


def _run_gx_silver(**ctx):
    from gx.run_silver_suite import run
    run(env=ENV, ingestion_date=ctx["ds"])


def _slack_fail(context):
    SlackWebhookOperator(
        task_id="slack_fail",
        slack_webhook_conn_id="slack_webhook",
        message=f"❌ *silver_transforms_dag* FAILED | task: {context['task_instance'].task_id} | {context['ds']}",
    ).execute(context)


with DAG(
    dag_id="silver_transforms_dag",
    default_args={**default_args, "on_failure_callback": _slack_fail},
    schedule_interval=None,
    catchup=False,
    tags=["silver", "glue"],
) as dag:

    glue_application = GlueJobOperator(
        task_id="glue_silver_application",
        job_name="glue_silver_application",
        script_args=GLUE_ARGS,
        aws_conn_id="aws_default",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        num_of_dpus=2,
    )

    # Depends on application completing first — referential integrity GX check
    glue_bureau = GlueJobOperator(
        task_id="glue_silver_bureau",
        job_name="glue_silver_bureau",
        script_args=GLUE_ARGS,
        aws_conn_id="aws_default",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        num_of_dpus=2,
    )

    glue_prev_app = GlueJobOperator(
        task_id="glue_silver_prev_app",
        job_name="glue_silver_previous_application",
        script_args=GLUE_ARGS,
        aws_conn_id="aws_default",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        num_of_dpus=2,
    )

    glue_installments = GlueJobOperator(
        task_id="glue_silver_installments",
        job_name="glue_silver_installments",
        script_args=GLUE_ARGS,
        aws_conn_id="aws_default",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        num_of_dpus=2,
    )

    glue_balance = GlueJobOperator(
        task_id="glue_silver_balance_tables",
        job_name="glue_silver_balance_tables",
        script_args=GLUE_ARGS,
        aws_conn_id="aws_default",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        num_of_dpus=2,
    )

    gx_silver = PythonOperator(
        task_id="run_gx_silver_suite",
        python_callable=_run_gx_silver,
    )

    trigger_gold = TriggerDagRunOperator(
        task_id="trigger_gold_dag",
        trigger_dag_id="gold_dbt_dag",
        wait_for_completion=False,
    )

    # Dependency chain per PIPELINE_SPEC Section 5.2
    glue_application >> glue_bureau
    glue_application >> [glue_prev_app, glue_installments, glue_balance]
    [glue_bureau, glue_prev_app, glue_installments, glue_balance] >> gx_silver >> trigger_gold
