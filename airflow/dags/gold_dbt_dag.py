"""
gold_dbt_dag — dbt run (staging → snapshot → intermediate → mart) → dbt test → Slack.

Schedule: None (triggered by silver_transforms_dag via TriggerDagRunOperator)
dbt project: dbt_home_credit/ | profiles: dbt_home_credit/profiles.yml
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.utils.trigger_rule import TriggerRule

ENV = os.getenv("ENV", "dev")
DBT_DIR = "dbt_home_credit"
DBT_CMD = f"dbt --profiles-dir {DBT_DIR} --project-dir {DBT_DIR}"

default_args = {
    "owner": "raja-luqman",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _slack_alert(icon: str, context):
    task_id = context["task_instance"].task_id
    ds = context["ds"]
    duration = int((context["task_instance"].end_date - context["task_instance"].start_date).total_seconds()) if context["task_instance"].end_date else 0
    msg = f"[{ENV}] gold_dbt_dag {icon} | {ds} | task: {task_id} | {duration}s"
    SlackWebhookOperator(
        task_id="slack_notify",
        slack_webhook_conn_id="slack_webhook",
        message=msg,
    ).execute(context)


with DAG(
    dag_id="gold_dbt_dag",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["gold", "dbt", "snowflake"],
) as dag:

    dbt_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"{DBT_CMD} run --select staging --target {ENV}",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"{DBT_CMD} snapshot --target {ENV}",
    )

    dbt_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"{DBT_CMD} run --select intermediate --target {ENV}",
    )

    dbt_mart = BashOperator(
        task_id="dbt_run_mart",
        bash_command=f"{DBT_CMD} run --select mart --target {ENV}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT_CMD} test --target {ENV}",
    )

    slack_success = BashOperator(
        task_id="slack_notify_success",
        bash_command=f'curl -s -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" -d \'{{"text":"[{ENV}] gold_dbt_dag ✅ PASS | {{{{ ds }}}}"}}\'',
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    slack_failure = BashOperator(
        task_id="slack_notify_failure",
        bash_command=f'curl -s -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" -d \'{{"text":"[{ENV}] gold_dbt_dag ❌ FAIL | {{{{ ds }}}}"}}\'',
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    dbt_staging >> dbt_snapshot >> dbt_intermediate >> dbt_mart >> dbt_test >> [slack_success, slack_failure]
