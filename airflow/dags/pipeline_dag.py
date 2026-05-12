"""
Home Credit Risk Pipeline — Main DAG
Modelling : Kimball — Star Schema
Stack     : AWS Glue (Bronze+Silver) → dbt (Gold/Snowflake)
Schedule  : @daily
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'raja-luqman',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def slack_success(context):
    SlackWebhookOperator(
        task_id='slack_success',
        slack_webhook_conn_id='slack_webhook',
        message=f"✅ *home-credit-risk-pipeline* — Success | {context['ds']}",
    ).execute(context)

def slack_failure(context):
    SlackWebhookOperator(
        task_id='slack_failure',
        slack_webhook_conn_id='slack_webhook',
        message=f"❌ *home-credit-risk-pipeline* — FAILED: {context['task_instance'].task_id} | {context['ds']}",
    ).execute(context)

with DAG(
    dag_id='home_credit_risk_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    on_success_callback=slack_success,
    on_failure_callback=slack_failure,
    tags=['banking', 'credit-risk', 'kimball'],
) as dag:

    bronze_ingest = PythonOperator(
        task_id='bronze_ingest_7_tables',
        python_callable=lambda: __import__('bronze.bronze_pipeline', fromlist=['']).run(),
    )

    silver_glue = PythonOperator(
        task_id='silver_glue_transform',
        python_callable=lambda: __import__('silver.trigger_glue_job', fromlist=['']).run(),
    )

    silver_dq = PythonOperator(
        task_id='silver_dq_gx_check',
        python_callable=lambda: __import__('data_quality.run_silver_suite', fromlist=['']).run(),
    )

    gold_run = BashOperator(
        task_id='gold_dbt_run',
        bash_command='dbt run --profiles-dir gold --project-dir gold',
    )

    gold_test = BashOperator(
        task_id='gold_dbt_test',
        bash_command='dbt test --profiles-dir gold --project-dir gold',
    )

    bronze_ingest >> silver_glue >> silver_dq >> gold_run >> gold_test
