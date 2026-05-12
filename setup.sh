#!/bin/bash
# =============================================================================
# HOME CREDIT RISK PIPELINE — SCAFFOLD v1.0
# Stack    : AWS Glue + S3 + Snowflake + dbt + GX + Airflow
# Dataset  : Kaggle Competition — home-credit-default-risk
# Modelling: Kimball — Star Schema
# Cloud    : AWS primary
# Run      : bash setup.sh
# =============================================================================

PROJECT_NAME="home-credit-risk-pipeline"
DOMAIN="banking"
DATASET="Home Credit Default Risk"
CLOUD="aws"
MODELLING="Kimball"
GRAIN="fact_loan_application: 1 row = 1 loan application"
KAGGLE_COMPETITION="home-credit-default-risk"
DEV_SAMPLE_ROWS=1000

echo ""
echo "🚀 $PROJECT_NAME — scaffold start"
echo "   Domain    : $DOMAIN"
echo "   Dataset   : $DATASET"
echo "   Cloud     : $CLOUD"
echo "   Modelling : $MODELLING"
echo ""

# =============================================================================
# FOLDERS
# =============================================================================

mkdir -p docs/ADR
mkdir -p docs/screenshots
mkdir -p bronze
mkdir -p silver
mkdir -p gold/dbt_models/staging
mkdir -p gold/dbt_models/intermediate
mkdir -p gold/dbt_models/marts
mkdir -p data_quality/expectations
mkdir -p data_quality/checkpoints
mkdir -p airflow/dags
mkdir -p airflow/plugins
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p infrastructure/terraform
mkdir -p infrastructure/credentials
mkdir -p sign-offs
mkdir -p .claude/agents
mkdir -p data

echo "✅ Folders created"

# =============================================================================
# .claude/agents/ — 14 Agent Persona Files
# =============================================================================

cat > .claude/agents/01-business-analyst.md << 'EOF'
# Business Analyst (BA)

## Identity
Experienced BA. Neutral, business-value focused.
Translate business problems → data requirements.

## Personality
Positif : Terima idea kalau ada clear business justification
Negatif : "Apa business impact dia? Kalau tak boleh jawab, scope out."

## Responsibilities
- Define stakeholders, use cases, KPIs
- Business rules dan metric formulas
- Validate setiap feature ada business value
- Flag immediately kalau nampak scope creep

## Rules
- WAJIB baca docs/BRD.md sebelum respond
- Jangan assume requirement yang tak dibincang
- KPI formula kena explicit — jangan vague
EOF

cat > .claude/agents/02-product-owner.md << 'EOF'
# Product Owner (PO)

## Identity
Scope-obsessed. Prioritize ruthlessly. Delivery-focused.

## Personality
Positif : Setuju kalau in-scope, high-value, realistic
Negatif : "Nice to have. Phase 2. Move on."

## Responsibilities
- Maintain scope boundary
- Break work into phases
- Challenge every feature: "Perlu ke sekarang?"
- Ensure deliverable realistic untuk Codespace constraint

## Priority Framework
Must Have  : Business critical, blocking downstream
Should Have: Important tapi not blocking → Phase 2
Could Have : Nice to have → Phase 3
Won't Have : Out of scope
EOF

cat > .claude/agents/03-data-architect.md << 'EOF'
# Data Architect (DA)

## Identity
Own data modelling end-to-end. Conceptual → Logical → Physical.
Collaborate rapat dengan DPE untuk feasibility.

## Personality
Positif : Setuju kalau model sound, grain clear, paradigm justified
Negatif : "Grain belum defined. AE tak boleh build dulu."

## Data Model (LOCKED — dari Step 3 Claude.ai session)
Paradigm : Kimball — Star Schema
Facts:
  fact_loan_application    — grain: 1 row = 1 application (SK_ID_CURR)
  fact_installment_payment — grain: 1 row = 1 installment payment
  fact_bureau_credit       — grain: 1 row = 1 bureau record per applicant
Dims:
  dim_applicant     — SCD Type 2 (start_date, end_date, is_current)
  dim_loan_type     — SCD Type 1
  dim_credit_status — SCD Type 1

## Hard Rules
- Grain LOCKED — jangan reopen debate
- SCD Type 2 untuk dim_applicant = non-negotiable (resume proof)
- Silver transforms = AWS Glue SAHAJA — bukan Databricks
- WAJIB baca docs/DRD.md dan docs/DATA_MODEL.md sebelum respond
EOF

cat > .claude/agents/04-senior-data-engineer.md << 'EOF'
# Senior Data Engineer (SDE)

## Identity
8 tahun experience. Architecture-first.
Zero tolerance untuk shortcuts yang jadi technical debt.

## Personality
Positif : Setuju kalau scalable, maintainable, production-grade
Negatif : "Ini akan break. Kenapa? Sebab..."

## Responsibilities
- Architecture decisions + ADRs
- Code review — enforce idempotency, null handling, partitioning
- Challenge tech choices dengan justifikasi
- Review sebelum cloud promote

## Non-Negotiables
- Idempotent pipelines (MERGE bukan INSERT)
- Explicit null handling
- Partition strategy defined
- SHA-256 PII masking BEFORE write ke Silver
- Stack HANYA dari resume
EOF

cat > .claude/agents/05-data-engineer.md << 'EOF'
# Data Engineer (DE)

## Identity
Hands-on builder. Execute ikut SPEC yang locked.

## Responsibilities
- Build Bronze layer (ingest 7 CSVs + metadata)
- Build Silver layer (AWS Glue Spark transforms)
- PII masking: SHA-256 pada quasi-identifier columns
- Unit tests setiap function

## Critical Notes
- Kaggle Competition download: kaggle competitions download -c home-credit-default-risk
- BUKAN kaggle datasets download
- Silver = AWS Glue job (Spark) — BUKAN PySpark local untuk cloud
- Dev = PySpark local mode untuk unit test sahaja
- Partition Bronze by ingestion_date

## Code Standards
- WHAT/WHY/WHEN comments
- Idempotent — MERGE bukan INSERT
- NULL handling explicit
- Log errors ke quarantine table
EOF

cat > .claude/agents/06-analytics-engineer.md << 'EOF'
# Analytics Engineer (AE)

## Identity
Own Gold layer dan dbt models.

## Data Model (LOCKED)
staging__home_credit_applications.sql
staging__home_credit_bureau.sql
staging__home_credit_installments.sql
int_applicant_scd2.sql            <- SCD Type 2 logic here
int_credit_risk_features.sql
mart_loan_application.sql         <- fact_loan_application
mart_applicant_dim.sql            <- dim_applicant (SCD2)
mart_credit_risk_summary.sql      <- KPI mart

## KPIs to Implement
- default_rate = COUNT(TARGET=1) / COUNT(*) per segment
- avg_credit_amount = AVG(AMT_CREDIT) per loan_type
- bureau_delinquency_rate = COUNT(bureau bad records) / total bureau records

## Hard Rules
- WAJIB baca DATA_MODEL.md sebelum build
- SCD Type 2 implementation: start_date, end_date, is_current
- Grain dari DATA_MODEL.md = non-negotiable
EOF

cat > .claude/agents/07-data-platform-engineer.md << 'EOF'
# Data Platform Engineer (DPE)

## Identity
Own infrastructure. Cost-aware. AWS specialist untuk projek ni.

## Stack untuk Projek Ni (LOCKED)
Bronze  : AWS Glue (Spark) ingestion → S3 Delta
Silver  : AWS Glue (Spark) transforms → S3 Delta
Gold    : dbt Core → Snowflake
Query   : Databricks Serverless SQL (query only)

## CRITICAL: Databricks Constraint
⚠️ Databricks = Serverless SQL ONLY
⚠️ No Classic Compute, no PySpark jobs
⚠️ Guna untuk SQL analytics queries SAHAJA
⚠️ Silver transforms MESTI guna AWS Glue

## AWS Free Tier Limits
S3    : 5GB — monitor usage
Glue  : 1M DPU-second — monitor closely

## Feasibility Checklist
[ ] AWS Glue job memory sufficient untuk 7 CSV files?
[ ] S3 storage dalam 5GB limit untuk dev?
[ ] Snowflake credit sustainable?
[ ] Airflow standalone connections configured?
EOF

cat > .claude/agents/08-data-quality-steward.md << 'EOF'
# Data Quality Steward (DQS)

## Identity
Paranoid pasal data quality. PII compliance focus untuk projek ni.

## PII Masking Strategy (LOCKED)
Columns to SHA-256 mask dalam Silver:
  DAYS_BIRTH (age proxy)
  DAYS_EMPLOYED
Method: hashlib.sha256(str(value).encode()).hexdigest()
Timing: Bronze → Silver transform (Glue job)
GX Check: masked != original value

## GX Suites
bronze_suite : row count, schema match, ingestion_ts not null
silver_suite : PII masked, nulls handled, dedup verified
gold_suite   : FK integrity, KPI not null, dbt tests pass

## Referential Integrity
fact_loan_application.applicant_id → dim_applicant.applicant_id
fact_installment_payment.SK_ID_CURR → fact_loan_application.SK_ID_CURR
fact_bureau_credit.SK_ID_CURR → fact_loan_application.SK_ID_CURR
EOF

cat > .claude/agents/09-project-manager.md << 'EOF'
# Project Manager (PM)

## Identity
Enforce timeline. Zero tolerance untuk open loops.

## Responsibilities
- Facilitate sign-off gates
- Track blockers + assign owners
- Enforce 3-round debate limit
- Update PROJECT_STATUS.md

## Pre-Locked Decisions (jangan reopen)
✅ Paradigm: Kimball
✅ Grain: locked per fact table
✅ SCD: dim_applicant = Type 2
✅ Cloud: AWS primary
✅ Databricks: SQL only
EOF

cat > .claude/agents/10-qa-engineer.md << 'EOF'
# QA Engineer (QA)

## Test Checklist

### Bronze (7 tables)
[ ] Row count match source CSV
[ ] ingestion_ts populated
[ ] Schema match DRD per table
[ ] Partition created by date

### Silver
[ ] SHA-256 masking applied (DAYS_BIRTH, DAYS_EMPLOYED)
[ ] Dedup successful per SK_ID_CURR
[ ] Null handling applied
[ ] Quarantine table populated

### Gold (dbt)
[ ] dbt run success
[ ] dbt test pass
[ ] SCD Type 2 correct (is_current, start_date, end_date)
[ ] FK integrity pass

### Airflow
[ ] All tasks green
[ ] Slack alert fired
[ ] Retry logic works

Evidence: screenshot semua result → docs/screenshots/
EOF

cat > .claude/agents/11-finops-agent.md << 'EOF'
# FinOps Agent

## Token Rules
Discussion/debate → Sonnet
Code generation  → Haiku
Boilerplate      → Haiku

## Cloud Cost Rules (projek ni)
AWS Glue  : Monitor DPU — 1M limit
S3        : Monitor 5GB — 7 large CSVs berisiko
Snowflake : Gold ONLY
Databricks: SQL queries sahaja — no compute cost dari Spark

## Cost Flags
- bureau_balance.csv = 27M rows — Glue DPU akan tinggi
- installments_payments.csv = 13M rows — sama
- Dev: sample 1000 rows sahaja untuk jimat DPU
EOF

cat > .claude/agents/12-scope-guardian.md << 'EOF'
# Scope Guardian

## Veto Triggers
1. Tools yang tak dalam resume
2. Column yang tak dalam DRD.md
3. Same topic >3 rounds
4. Suggest Spark jobs kat Databricks (Serverless SQL only!)
5. AE build tanpa grain locked

## Portfolio Scope
✅ 7-table Bronze ingestion
✅ AWS Glue Silver transforms + SHA-256 masking
✅ dbt Gold + SCD Type 2
✅ GX suites per layer
✅ Airflow DAG + Slack alert
✅ Screenshot evidence
❌ ML model prediction (out of scope)
❌ Databricks Spark jobs
EOF

cat > .claude/agents/13-mcp-orchestrator.md << 'EOF'
# MCP Orchestrator

## Tool Assignments
Snowflake  → mcp_snowflake
AWS        → mcp_aws-docs
dbt        → mcp_dbt
Databricks → mcp_databricks (SQL queries only)

## Announcement Format
🔧 MCP ORCHESTRATOR — Tools This Phase:
[tool]: [capability]
EOF

cat > .claude/agents/14-git-agent.md << 'EOF'
# Git Agent

## Hard Rules
1. JANGAN commit: CLAUDE.md, .claude/, PROJECT_STATUS.md,
   COST_LOG.md, JOURNEY_LOG.md, sign-offs/, .env.*
2. JANGAN ada Co-authored-by
3. Format: [Phase X] [Document] — [summary]

## Files Per Phase
Phase 1 : docs/BRD.md
Phase 2 : docs/DRD.md, docs/DATA_DICTIONARY.md
Phase 3 : docs/ARCHITECTURE.md, docs/PIPELINE_SPEC.md, docs/DATA_MODEL.md
Phase 4a: bronze/, silver/, gold/, tests/, airflow/dags/
Phase 4b: docs/screenshots/
Phase 5 : docs/DQD.md, docs/OPS_RUNBOOK.md, data_quality/
EOF

echo "✅ 14 agent persona files created"

# =============================================================================
# .claude/settings.json
# =============================================================================

cat > .claude/settings.json << 'EOF'
{
  "includeCoAuthoredBy": false,
  "model": "claude-sonnet-4-6",
  "context": {
    "autoLoadFiles": [
      "CLAUDE.md",
      "PROJECT_STATUS.md"
    ]
  }
}
EOF

echo "✅ .claude/settings.json created"

# =============================================================================
# .gitignore
# =============================================================================

cat > .gitignore << 'EOF'
# Claude
CLAUDE.md
.claude/
HOW_IT_WORKS.txt
PROJECT_STATUS.md
COST_LOG.md
docs/JOURNEY_LOG.md
docs/INTERVIEW_GUIDE.md
sign-offs/

# Credentials
.env
.env.dev
.env.staging
.env.prod
*.env
credentials/

# Data
*.parquet
*.csv
*.xlsx
data/
raw/

# Python
__pycache__/
*.pyc
.venv/
venv/

# dbt
.dbt/
dbt_packages/
target/

# Airflow
airflow/logs/
airflow.cfg
airflow.db
standalone_admin_password.txt

# Logs
logs/
*.log

# IDE
.vscode/settings.json
.idea/
.DS_Store
EOF

echo "✅ .gitignore created"

# =============================================================================
# .env.example
# =============================================================================

cat > .env.example << 'EOF'
# home-credit-risk-pipeline — Credential Template
# Copy ke .env.dev / .env.staging / .env.prod
# JANGAN commit mana-mana .env

ENV=dev
CLOUD=aws

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-southeast-1
S3_BUCKET_DEV=home-credit-risk-dev
S3_BUCKET_STAGING=home-credit-risk-staging
S3_BUCKET_PROD=home-credit-risk-prod
GLUE_JOB_NAME=home-credit-silver-transform

# Databricks (Serverless SQL ONLY — no Classic Compute)
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
DATABRICKS_TOKEN=
DATABRICKS_SQL_WAREHOUSE_ID=

# Snowflake
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=HOME_CREDIT_RISK
SNOWFLAKE_SCHEMA_DEV=DEV
SNOWFLAKE_SCHEMA_STAGING=STAGING
SNOWFLAKE_SCHEMA_PROD=PROD
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=SYSADMIN

# Airflow
AIRFLOW__CORE__FERNET_KEY=
AIRFLOW__WEBSERVER__SECRET_KEY=

# Slack
SLACK_WEBHOOK_URL=
SLACK_CHANNEL=#data-pipeline-alerts

# dbt
DBT_PROFILES_DIR=./gold

# Kaggle — Competition Format (BUKAN standard dataset)
# Accept rules dulu: kaggle.com/competitions/home-credit-default-risk
# NOTE: KAGGLE_FILENAME tidak diperlukan untuk competition format.
#       Competition download semua files sekaligus via:
#       kaggle competitions download -c home-credit-default-risk
#       (Standard dataset guna KAGGLE_FILENAME — competition tak perlu)
KAGGLE_USERNAME=
KAGGLE_KEY=
KAGGLE_COMPETITION=home-credit-default-risk

# Dataset path (auto-set by download_dataset.py — jangan edit manual)
DATASET_SOURCE_PATH=
DEV_SAMPLE_ROWS=1000
EOF

echo "✅ .env.example created"

# =============================================================================
# .mcp.json
# =============================================================================

cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "snowflake": {
      "command": "uvx",
      "args": ["mcp-server-snowflake"],
      "env": {
        "SNOWFLAKE_ACCOUNT": "${SNOWFLAKE_ACCOUNT}",
        "SNOWFLAKE_USER": "${SNOWFLAKE_USER}",
        "SNOWFLAKE_PASSWORD": "${SNOWFLAKE_PASSWORD}",
        "SNOWFLAKE_DATABASE": "${SNOWFLAKE_DATABASE}",
        "SNOWFLAKE_WAREHOUSE": "${SNOWFLAKE_WAREHOUSE}"
      }
    },
    "databricks": {
      "command": "databricks",
      "args": ["mcp", "serve"],
      "env": {
        "DATABRICKS_HOST": "${DATABRICKS_HOST}",
        "DATABRICKS_TOKEN": "${DATABRICKS_TOKEN}"
      }
    },
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"]
    },
    "dbt": {
      "command": "dbt-mcp",
      "args": [],
      "env": {
        "DBT_PROFILES_DIR": "${DBT_PROFILES_DIR}"
      }
    }
  }
}
EOF

echo "✅ .mcp.json created"

# =============================================================================
# bronze/download_dataset.py — Competition format
# =============================================================================

cat > bronze/download_dataset.py << 'PYEOF'
"""
WHAT : Download Home Credit dataset dari Kaggle Competition API
WHY  : Competition format berbeza dari standard dataset — kena guna
       kaggle competitions download, BUKAN kaggle datasets download
WHEN : Run sekali sebelum pipeline start

CRITICAL: ini Kaggle COMPETITION, bukan standard dataset.
Command: kaggle competitions download -c home-credit-default-risk

Usage:
  python bronze/download_dataset.py --env dev
  python bronze/download_dataset.py --env staging
  python bronze/download_dataset.py --env prod
"""

import os
import argparse
import logging
import zipfile
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# WHAT: 7 source files untuk Home Credit pipeline
# WHY : Semua kena ingest untuk justify "7 disparate source tables" dalam resume
ALL_FILES = [
    "application_train.csv",
    "bureau.csv",
    "bureau_balance.csv",
    "previous_application.csv",
    "installments_payments.csv",
    "POS_CASH_balance.csv",
    "credit_card_balance.csv",
]

PRIMARY_FILE = "application_train.csv"


def load_env(env: str):
    """
    WHAT : Load .env file ikut environment
    WHY  : Setiap env ada credentials berbeza
    WHEN : First step sebelum any operation
    """
    env_file = f".env.{env}"
    if not Path(env_file).exists():
        raise FileNotFoundError(
            f"{env_file} tidak wujud.\n"
            f"Run: cp .env.example {env_file} dan fill in credentials."
        )
    load_dotenv(env_file)
    log.info(f"Loaded {env_file}")


def validate_kaggle_credentials():
    """
    WHAT : Validate Kaggle credentials
    WHY  : Fail fast sebelum API call
    WHEN : Sebelum download
    """
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")
    if not username or not key:
        raise EnvironmentError(
            "KAGGLE_USERNAME dan KAGGLE_KEY mesti diset dalam .env.\n"
            "Setup: https://www.kaggle.com/settings → API → Create New Token"
        )
    os.environ["KAGGLE_USERNAME"] = username
    os.environ["KAGGLE_KEY"] = key
    log.info(f"Kaggle credentials validated — user: {username}")


def download_competition_dataset(dest_dir: str = "data") -> str:
    """
    WHAT : Download Home Credit competition dataset dari Kaggle
    WHY  : Competition format — guna kaggle competitions download
           BUKAN kaggle datasets download (akan fail dengan 403)
    WHEN : Run sekali, skip kalau files dah ada
    Returns: path to data directory
    """
    import kaggle

    competition = os.getenv("KAGGLE_COMPETITION", "home-credit-default-risk")
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    # WHAT: Check kalau primary file dah ada — skip download
    primary_path = dest_path / PRIMARY_FILE
    if primary_path.exists():
        log.info(f"Dataset dah ada: {primary_path} — skip download")
        return str(dest_path)

    log.info(f"Downloading competition: {competition} → {dest_path}")
    log.info("⚠️  File besar — bureau_balance.csv = 27M rows. Ambil masa.")

    # WHAT: Download competition files
    # WHY : Competition API download dan auto-extract
    kaggle.api.competition_download_files(
        competition,
        path=str(dest_path),
        quiet=False
    )

    # WHAT: Unzip kalau perlu
    zip_path = dest_path / f"{competition}.zip"
    if zip_path.exists():
        log.info(f"Unzipping {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_path)
        zip_path.unlink()
        log.info("Unzip complete")

    # WHAT: Verify semua 7 files ada
    missing = [f for f in ALL_FILES if not (dest_path / f).exists()]
    if missing:
        log.warning(f"Files missing selepas download: {missing}")
    else:
        log.info(f"✅ Semua {len(ALL_FILES)} files verified")

    return str(dest_path)


def sample_dev_data(data_dir: str, rows: int = 1000) -> str:
    """
    WHAT : Sample N rows dari application_train untuk dev
    WHY  : 307k rows terlalu besar untuk dev — sample jimat memory dan DPU
    WHEN : Dev environment SAHAJA
    Returns: path to sampled CSV
    """
    import pandas as pd

    source = Path(data_dir) / PRIMARY_FILE
    sample_path = Path(data_dir) / f"application_train_dev_{rows}rows.csv"

    if sample_path.exists():
        log.info(f"Dev sample dah ada: {sample_path} — skip")
        return str(sample_path)

    log.info(f"Sampling {rows} rows dari {source}...")
    df = pd.read_csv(source, nrows=rows)
    df.to_csv(sample_path, index=False)
    log.info(f"Dev sample saved: {sample_path} ({len(df)} rows)")
    return str(sample_path)


def upload_all_to_s3(data_dir: str, env: str) -> dict:
    """
    WHAT : Upload semua 7 CSV ke S3 landing zone
    WHY  : S3 = single source of truth untuk staging/prod pipeline
    WHEN : Staging + prod environment
    Returns: dict of {filename: s3_path}
    """
    import boto3

    bucket = os.getenv(f"S3_BUCKET_{env.upper()}")
    region = os.getenv("AWS_REGION", "ap-southeast-1")

    if not bucket:
        raise EnvironmentError(f"S3_BUCKET_{env.upper()} tidak diset")

    s3 = boto3.client("s3", region_name=region)
    uploaded = {}

    for filename in ALL_FILES:
        local_path = Path(data_dir) / filename
        if not local_path.exists():
            log.warning(f"File tak jumpa — skip: {filename}")
            continue

        s3_key = f"landing/{filename}"
        s3_path = f"s3://{bucket}/{s3_key}"

        # WHAT: Skip kalau dah ada dengan size sama — jimat S3 PUT cost
        try:
            resp = s3.head_object(Bucket=bucket, Key=s3_key)
            if resp["ContentLength"] == local_path.stat().st_size:
                log.info(f"Skip (same size): {s3_path}")
                uploaded[filename] = s3_path
                continue
        except Exception:
            pass

        size_mb = local_path.stat().st_size / (1024 * 1024)
        log.info(f"Uploading {filename} ({size_mb:.1f} MB) → {s3_path}")
        s3.upload_file(str(local_path), bucket, s3_key)
        uploaded[filename] = s3_path
        log.info(f"✅ {filename} uploaded")

    return uploaded


def main():
    parser = argparse.ArgumentParser(
        description="Download Home Credit competition dataset dari Kaggle"
    )
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"])
    parser.add_argument("--rows", type=int, default=None)
    args = parser.parse_args()

    log.info(f"=== Dataset Acquisition — env: {args.env} ===")

    load_env(args.env)
    validate_kaggle_credentials()

    data_dir = download_competition_dataset(dest_dir="data")

    if args.env == "dev":
        dev_rows = args.rows or int(os.getenv("DEV_SAMPLE_ROWS", "1000"))
        sample_path = sample_dev_data(data_dir, rows=dev_rows)
        log.info(f"=== Done — dev dataset: {sample_path} ===")
        log.info(f"Set DATASET_SOURCE_PATH={sample_path} dalam .env.dev")
    else:
        uploaded = upload_all_to_s3(data_dir, env=args.env)
        log.info(f"=== Done — {len(uploaded)} files uploaded ke S3 ===")
        for fname, path in uploaded.items():
            log.info(f"  {fname} → {path}")
        log.info(f"Set DATASET_SOURCE_PATH=s3://[bucket]/landing/ dalam .env.{args.env}")


if __name__ == "__main__":
    main()
PYEOF

echo "✅ bronze/download_dataset.py created (Competition format)"

# =============================================================================
# Airflow DAG
# =============================================================================

cat > airflow/dags/pipeline_dag.py << 'EOF'
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
EOF

echo "✅ Airflow DAG created"

# =============================================================================
# dbt profiles.yml
# =============================================================================

cat > gold/profiles.yml << 'EOF'
home-credit-risk-pipeline:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'SYSADMIN') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA_DEV') }}"
      threads: 4
    staging:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'SYSADMIN') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA_STAGING') }}"
      threads: 4
    prod:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'SYSADMIN') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA_PROD') }}"
      threads: 4
EOF

echo "✅ dbt profiles.yml created"

# =============================================================================
# Placeholder docs
# =============================================================================

cat > docs/BRD.md << 'EOF'
# BRD: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 1 sign-off
> Domain: Banking | Dataset: Home Credit Default Risk

## Stakeholders
| Stakeholder | Role | Data Need |
|-------------|------|-----------|
| Risk Team | Primary consumer | Default rate by segment |
| Compliance | Audit | PII masking evidence, SCD audit trail |
| Portfolio Mgmt | Secondary | Loan portfolio health KPIs |

## Business Requirements
1. Ingest 300k+ credit records dari 7 source tables
2. Mask PII/quasi-identifiers (SHA-256) sebelum analytics layer
3. Track applicant history via SCD Type 2
4. Surface credit risk KPIs dalam Gold layer

## KPIs
| KPI | Formula | Frequency |
|-----|---------|-----------|
| Default Rate | COUNT(TARGET=1) / COUNT(*) | Daily |
| Avg Credit Amount | AVG(AMT_CREDIT) per loan_type | Daily |
| Bureau Delinquency Rate | Bureau bad / total bureau records | Daily |

## Sign-off Gate
| Agent | Status |
|-------|--------|
| BA | PENDING |
| PO | PENDING |
| PM | PENDING |
| DQS | PENDING |
EOF

cat > docs/DRD.md << 'EOF'
# DRD: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 2 sign-off

## Source Tables (7 files)
| File | Rows (approx) | Primary Key | Notes |
|------|--------------|-------------|-------|
| application_train.csv | 307,511 | SK_ID_CURR | Primary fact source |
| bureau.csv | 1,716,428 | SK_ID_BUREAU | Credit bureau records |
| bureau_balance.csv | 27,299,925 | SK_ID_BUREAU | Monthly bureau status |
| previous_application.csv | 1,670,214 | SK_ID_PREV | Past loan applications |
| installments_payments.csv | 13,605,401 | SK_ID_PREV | Payment history |
| POS_CASH_balance.csv | 10,001,358 | SK_ID_PREV | POS loan balance |
| credit_card_balance.csv | 3,840,312 | SK_ID_PREV | Credit card balance |

## Known Data Issues
| Issue | Table | Strategy |
|-------|-------|----------|
| XNA values | application_train (ORGANIZATION_TYPE) | Treat as NULL |
| 365243 magic number | DAYS_EMPLOYED | Flag as anomaly, quarantine |
| High cardinality | OCCUPATION_TYPE | NULL handling required |

## Ingestion Pattern
Static snapshot CSV — simulate CDC via MERGE upsert dalam Silver

## Sign-off Gate
| Agent | Status |
|-------|--------|
| BA | PENDING |
| DA | PENDING |
| SDE | PENDING |
| DPE | PENDING |
| DQS | PENDING |
| PM | PENDING |
EOF

cat > docs/DATA_DICTIONARY.md << 'EOF'
# Data Dictionary: Home Credit Risk Pipeline
> Owner: DQS

## Key Business Terms
| Term | Definition |
|------|-----------|
| Default | TARGET=1 — applicant gagal bayar loan |
| SK_ID_CURR | Unique applicant ID across all tables |
| AMT_CREDIT | Total credit amount applied |
| DAYS_BIRTH | Days since birth (negative integer) |
| DAYS_EMPLOYED | Days since employment start (365243 = anomaly) |

## PII / Quasi-Identifiers (SHA-256 masked dalam Silver)
| Column | Risk | Mask Method |
|--------|------|-------------|
| DAYS_BIRTH | Age proxy | SHA-256 |
| DAYS_EMPLOYED | Employment proxy | SHA-256 |
EOF

cat > docs/DATA_MODEL.md << 'EOF'
# Data Model: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 3 sign-off
> Paradigm: Kimball — Star Schema (LOCKED dari Claude.ai session)

## Paradigm Decision
Chosen  : Kimball — Star Schema
Reason  : Analytics aggregation, AWS Glue manageable joins,
          Snowflake cost predictable, resume entry alignment

## Why Not OBT
OBT rejected — bureau_balance 27M rows + installments 13M rows
nested Arrays = memory risk. Kimball Star Schema = safer untuk free tier.

## Fact Tables
### fact_loan_application
- Grain   : 1 row = 1 loan application (SK_ID_CURR) — LOCKED
- Source  : application_train.csv
- Pattern : Snapshot → MERGE upsert

### fact_installment_payment
- Grain   : 1 row = 1 installment payment record — LOCKED
- Source  : installments_payments.csv
- Pattern : Append + dedup

### fact_bureau_credit
- Grain   : 1 row = 1 bureau credit record per applicant — LOCKED
- Source  : bureau.csv
- Pattern : Snapshot → MERGE

## Dimension Tables
### dim_applicant — SCD TYPE 2 — LOCKED (resume proof)
- Columns : applicant_id, income, employment, start_date, end_date, is_current
- Source  : application_train.csv

### dim_loan_type — SCD TYPE 1
- Columns : loan_type_id, loan_type_name
- Source  : NAME_CONTRACT_TYPE dari application_train

### dim_credit_status — SCD TYPE 1
- Columns : status_id, status_code, status_description
- Source  : Credit bureau status codes

## Sign-off Gate
| Agent | Status |
|-------|--------|
| DA | PENDING |
| DPE | PENDING |
| SDE | PENDING |
| AE | PENDING |
| PM | PENDING |
EOF

cat > docs/ARCHITECTURE.md << 'EOF'
# Architecture: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 3 sign-off

## Stack
| Layer | Tool | Notes |
|-------|------|-------|
| Storage | AWS S3 | Landing + Bronze + Silver |
| Bronze | Delta Lake on S3 | ACID, time travel |
| Silver | AWS Glue (Spark) | SHA-256 masking, transforms |
| Gold | dbt Core + Snowflake | Kimball Star Schema |
| Orchestration | Airflow standalone | localhost:8080 |
| Quality | Great Expectations | Per layer |
| BI | Power BI | Gold consumer |
| Analytics | Databricks Serverless SQL | Query layer only |

## CRITICAL Constraint
Databricks = Serverless SQL ONLY. No PySpark. No Classic Compute.
Silver transforms = AWS Glue (Spark) SAHAJA.

## Data Flow
application_train.csv (307k)  ─┐
bureau.csv (1.7M)              ├─→ S3 Landing → Bronze (Delta)
bureau_balance.csv (27M)       ├─→ AWS Glue Silver → SHA-256 mask
installments_payments.csv      ├─→ dbt Gold → Snowflake → Power BI
POS_CASH_balance.csv           ├─→
credit_card_balance.csv        ─┘
EOF

cat > docs/PIPELINE_SPEC.md << 'EOF'
# Pipeline SPEC: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 3 sign-off

## Bronze Layer
Input  : 7 CSV files dari S3 landing/ (atau local dev)
Output : bronze.{table} (Delta Lake, partitioned by ingestion_date)
Logic  : Store as-is + ingestion_ts, source_file, batch_id, env

## Silver Layer (AWS Glue Spark Job)
Input  : bronze.{table}
Output : silver.{table}

Transforms:
1. DEDUP       : Keep latest ingestion_ts per SK_ID_CURR
2. TYPE CAST   : DAYS_BIRTH → Integer, AMT_CREDIT → Float
3. NULL HANDLE : DAYS_EMPLOYED = 365243 → NULL + flag
                 ORGANIZATION_TYPE = 'XNA' → NULL
4. PII MASK    : SHA-256(DAYS_BIRTH), SHA-256(DAYS_EMPLOYED)
5. SCD PREP    : Add is_current, start_date, end_date untuk dim_applicant

## Gold Layer (dbt)
staging__applications.sql       → clean + cast
staging__bureau.sql             → clean + cast
int_applicant_scd2.sql          → SCD Type 2 logic
int_credit_risk_features.sql    → join fact tables
mart_loan_application.sql       → fact_loan_application
mart_applicant_dim.sql          → dim_applicant (SCD2)
mart_credit_risk_summary.sql    → KPI aggregations

## KPIs
default_rate            = COUNT(TARGET=1) / COUNT(*)
avg_credit_amount       = AVG(AMT_CREDIT) GROUP BY loan_type
bureau_delinquency_rate = SUM(bad_bureau_records) / COUNT(bureau_records)
EOF

cat > docs/DQD.md << 'EOF'
# DQD: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 5 sign-off

## Bronze Suite
| Check | Rule | Severity |
|-------|------|----------|
| application_train row count | = 307,511 (staging) | CRITICAL |
| ingestion_ts | NOT NULL | CRITICAL |
| SK_ID_CURR | NOT NULL | CRITICAL |

## Silver Suite
| Check | Rule | Severity |
|-------|------|----------|
| DAYS_BIRTH masked | != original value | CRITICAL |
| DAYS_EMPLOYED masked | != original value | CRITICAL |
| DAYS_EMPLOYED anomaly | 365243 → NULL | HIGH |
| SK_ID_CURR | UNIQUE per table | HIGH |

## Gold Suite (dbt tests)
| Check | Rule | Severity |
|-------|------|----------|
| fact_loan_application.SK_ID_CURR | NOT NULL, UNIQUE | CRITICAL |
| dim_applicant.is_current | Only 1 True per applicant | CRITICAL |
| FK: fact → dim_applicant | Referential integrity | CRITICAL |
EOF

cat > docs/OPS_RUNBOOK.md << 'EOF'
# OPS Runbook: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 5 sign-off

## Monitoring
| Tool | Where |
|------|-------|
| Airflow | localhost:8080 |
| AWS Glue | AWS Console → Glue → Jobs |
| GX Report | docs/screenshots/gx_report.html |
| Snowflake | Snowflake UI |

## Scenarios

### Bronze fail
Check : S3 landing/ ada files?
Fix   : Rerun download_dataset.py → Rerun bronze task

### Glue Silver fail
Check : AWS Glue → Jobs → Logs
Fix 1 : Schema mismatch → update Silver job
Fix 2 : DPU limit → optimize Glue job
Rerun : Airflow → Clear silver_glue_transform → Trigger

### dbt test fail
Check : dbt test output
Fix 1 : FK violation → check Silver quarantine
Fix 2 : SCD is_current > 1 per applicant → check int_applicant_scd2.sql
EOF

echo "✅ Placeholder docs created (9 files)"

# =============================================================================
# ADR
# =============================================================================

cat > docs/ADR/ADR-001-kimball-star-schema.md << 'EOF'
# ADR-001: Data Modelling Paradigm — Kimball Star Schema

Status: Accepted
Date  : 2026-05-12
Owner : Data Architect + Data Platform Engineer

## Context
Home Credit dataset: 7 CSV files, 300k+ applicants, analytics use case.

## Decision
Paradigm: Kimball — Star Schema

## Consequences
(+) Standard analytics pattern — joins manageable dalam AWS Glue
(+) Snowflake query cost predictable
(+) SCD Type 2 directly proves resume bullet point
(-) More joins vs OBT
(-) bureau_balance (27M rows) needs careful partitioning

## Alternatives Rejected
OBT: rejected — bureau_balance 27M rows + installments 13M rows
     nested Array/Struct = memory risk + Snowflake cost unpredictable
EOF

echo "✅ ADR-001 created"

# =============================================================================
# requirements.txt
# =============================================================================

cat > requirements.txt << 'EOF'
# Core
pandas==2.1.0
python-dotenv==1.0.0
delta-spark==3.0.0

# Kaggle
kaggle==1.6.14

# AWS
boto3==1.34.0
awswrangler==3.5.0

# Airflow
apache-airflow==2.8.0
apache-airflow-providers-slack==8.0.0
apache-airflow-providers-amazon==8.0.0
apache-airflow-providers-snowflake==5.0.0
apache-airflow-providers-databricks==6.0.0

# Snowflake
snowflake-connector-python==3.6.0
snowflake-sqlalchemy==1.5.0

# dbt
dbt-core==1.7.0
dbt-snowflake==1.7.0

# Quality
great-expectations==0.18.0

# Testing
pytest==7.4.0
pytest-cov==4.1.0

# Utils
PyYAML==6.0.1
EOF

echo "✅ requirements.txt created"

# =============================================================================
# infrastructure/credentials/SETUP_GUIDE.txt
# =============================================================================

cat > infrastructure/credentials/SETUP_GUIDE.txt << 'EOF'
=== SETUP GUIDE — Home Credit Risk Pipeline ===
Stack: AWS (S3+Glue) + Snowflake + Databricks Serverless SQL + Airflow + Kaggle

STEP 1 — Copy env template
  cp .env.example .env.dev
  Fill in: KAGGLE_USERNAME, KAGGLE_KEY dulu

STEP 2 — Kaggle Competition Download
  Setup: https://www.kaggle.com/settings → API → Create New Token
  ⚠️ WAJIB accept competition rules dulu:
     https://www.kaggle.com/competitions/home-credit-default-risk → Join
  
  Download dev dataset:
    python bronze/download_dataset.py --env dev
  
  ⚠️ CRITICAL: Competition dataset — BUKAN standard dataset
  CORRECT: kaggle competitions download -c home-credit-default-risk
  WRONG  : kaggle datasets download (akan 403)

STEP 3 — AWS Setup
  IAM → Create User → AmazonS3FullAccess + AWSGlueConsoleFullAccess
  Create S3 buckets:
    aws s3 mb s3://home-credit-risk-dev
    aws s3 mb s3://home-credit-risk-staging
  Fill .env.dev: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

STEP 4 — Databricks (Serverless SQL ONLY)
  ⚠️ NO Classic Compute — Serverless SQL Warehouse sahaja
  Settings → SQL Warehouses → Copy warehouse ID
  Fill .env.dev: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_SQL_WAREHOUSE_ID

STEP 5 — Snowflake
  trial.snowflake.com → Register
  Run: CREATE DATABASE HOME_CREDIT_RISK;
  Fill .env.dev: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD

STEP 6 — Airflow Standalone
  pip install apache-airflow==2.8.0
  export AIRFLOW_HOME=$(pwd)/airflow
  airflow standalone
  UI: http://localhost:8080

STEP 7 — Verify All
  source .env.dev
  python -c "import kaggle; kaggle.api.authenticate(); print('Kaggle OK')"
  python -c "import boto3; boto3.client('s3').list_buckets(); print('AWS OK')"
  dbt debug --profiles-dir gold
EOF

echo "✅ SETUP_GUIDE.txt created"

# =============================================================================
# PROJECT_STATUS.md
# =============================================================================

cat > PROJECT_STATUS.md << 'EOF'
# PROJECT_STATUS.md — home-credit-risk-pipeline
Last updated : SETUP
Current phase: Phase 0 — Setup Complete
Modelling    : Kimball — Star Schema
Cloud        : AWS (S3 + Glue)
Databricks   : Serverless SQL ONLY (no PySpark jobs)

## Phase Overview
| Phase | Document | Status |
|-------|----------|--------|
| 0 | Setup | ✅ Done |
| 1 | BRD | ⏳ |
| 2 | DRD + Data Model Conceptual | ⏳ |
| 3 | Architecture + SPEC + Data Model Logical | ⏳ |
| 4a | CODE — local dev | ⏳ |
| 4b | CODE — cloud promote | ⏳ |
| 5 | DQD + OPS | ⏳ |

## Next Step When Resuming
1. Prompt: "Baca CLAUDE.md dan PROJECT_STATUS.md. Start Phase 1 — BRD."
2. Terus execute — jangan explain semula

## Pre-Locked Decisions (JANGAN reopen)
| Decision | Value |
|----------|-------|
| Paradigm | Kimball — Star Schema |
| fact_loan_application grain | 1 row = 1 application (SK_ID_CURR) |
| fact_installment_payment grain | 1 row = 1 payment record |
| fact_bureau_credit grain | 1 row = 1 bureau record |
| dim_applicant | SCD Type 2 |
| dim_loan_type | SCD Type 1 |
| dim_credit_status | SCD Type 1 |
| Cloud | AWS (S3 + Glue) |
| Databricks | Serverless SQL ONLY |
| PII masking | SHA-256 (DAYS_BIRTH, DAYS_EMPLOYED) |
EOF

echo "✅ PROJECT_STATUS.md created"

# =============================================================================
# COST_LOG.md
# =============================================================================

cat > COST_LOG.md << 'EOF'
# Cost Log: home-credit-risk-pipeline
> JANGAN commit

## Token Usage
| Phase | Sonnet | Haiku | Est. Cost |
|-------|--------|-------|-----------|
| 0 — Setup | - | - | $0.00 |
| Total | | | $0.00 |

## Cloud Usage
| Service | Used | Limit | Notes |
|---------|------|-------|-------|
| S3 | 0 GB | 5 GB | 7 large CSVs — monitor |
| Glue DPU | 0 | 1M | bureau_balance 27M rows = expensive |
| Snowflake | $0 | $400 | Gold only |
| Databricks | $0 | Trial | SQL queries only |
EOF

echo "✅ COST_LOG.md created"

# =============================================================================
# sign-offs/SIGN_OFF_LOG.md
# =============================================================================

cat > sign-offs/SIGN_OFF_LOG.md << 'EOF'
# Sign-off Log: home-credit-risk-pipeline
> JANGAN commit

## Phase 1 — BRD
Status: PENDING
| Agent | Decision |
|-------|----------|
| BA | PENDING |
| PO | PENDING |
| PM | PENDING |
| DQS | PENDING |

## Phase 2 — DRD
Status: PENDING
| Agent | Decision |
|-------|----------|
| BA | PENDING |
| DA | PENDING |
| SDE | PENDING |
| DPE | PENDING |
| DQS | PENDING |
| PM | PENDING |
EOF

echo "✅ sign-offs/SIGN_OFF_LOG.md created"

# =============================================================================
# docs/JOURNEY_LOG.md
# =============================================================================

cat > docs/JOURNEY_LOG.md << 'EOF'
# Journey Log: home-credit-risk-pipeline
> JANGAN commit

[001] [2026-05-12 · Phase 0]
DECISION  : Kimball Star Schema — 3 facts, 3 dims, SCD Type 2 untuk dim_applicant
AGENTS    : DA propose, DPE validate (Claude.ai session)
REASON    : Analytics aggregation, AWS Glue manageable, resume proof
TRADEOFF  : More joins vs OBT, tapi OBT = memory risk 27M row tables
OUTCOME   : Locked sebelum Claude Code — agents tak perlu reopen debate
STAR_NOTE : Y — "designed Star Schema untuk 300k+ applicant dataset"
LEARN     : Pre-lock decisions dalam Claude.ai jimat debate rounds dalam Claude Code
EOF

echo "✅ docs/JOURNEY_LOG.md created"

# =============================================================================
# docs/INTERVIEW_GUIDE.md — placeholder (JANGAN commit)
# Playbook v3.1 require placeholder ni — generated content selepas Phase 5
# =============================================================================

cat > docs/INTERVIEW_GUIDE.md << 'EOF'
# Interview Guide: home-credit-risk-pipeline
> Generated selepas Phase 5 selesai.
> Guna prompt: "Baca JOURNEY_LOG.md dan DATA_MODEL.md. Generate INTERVIEW_GUIDE.md"
> JANGAN commit file ni ke GitHub.

## Format Apabila Generated

### 1. Quick Reference Numbers
- Dataset size: 7 tables, 300k+ applicants, ~56M total rows
- Pipeline: Bronze (7 CSVs) → Silver (Glue Spark) → Gold (dbt/Snowflake)
- dbt models: [N] staging, [N] intermediate, [N] marts
- GX expectations: [N] checks per layer
- PII masking: SHA-256 on DAYS_BIRTH, DAYS_EMPLOYED

### 2. STAR Stories (3 strongest)
[Auto-generated dari JOURNEY_LOG.md selepas Phase 5]

### 3. What Went Wrong + Lesson
[Auto-generated]

### 4. What I Would Do Differently
[Auto-generated]

### 5. Data Model Decision Logic
- Kenapa Kimball bukan OBT?
  → bureau_balance 27M rows + installments 13M rows nested Arrays = OOM risk
  → Kimball Star Schema = safer, cost predictable, resume-aligned
- Kenapa SCD Type 2 untuk dim_applicant?
  → Resume bullet: "versioned audit trail for compliance requirements"
  → Full history backfill-safe via Delta Lake time travel

### 6. Architecture Decision Logic
- Kenapa AWS Glue untuk Silver bukan Databricks?
  → Databricks = Serverless SQL only, no Classic Compute
  → Glue = managed Spark, pay-per-DPU, no cluster management

### 7. Common Interview Q&A
[Auto-generated]

### 8. Questions to Ask Interviewer
[Auto-generated]
EOF

echo "✅ docs/INTERVIEW_GUIDE.md placeholder created"

# =============================================================================
# HOW_IT_WORKS.txt
# =============================================================================

cat > HOW_IT_WORKS.txt << 'EOF'
=== HOW THIS PROJECT WORKS ===
(JANGAN COMMIT)

Goal: Realisasikan resume entry "Banking Credit Risk Pipeline"
      dengan actual code + GitHub evidence.

Resume bullets to prove:
1. "300k+ records from 7 disparate source tables" → Bronze 7-table ingestion
2. "GX + PII masking SHA-256" → Silver Glue job + GX suite
3. "SCD Type 2 for applicant dimensions" → dim_applicant dalam Gold

Stack (locked):
  Ingest  : Python + Kaggle Competition API
  Bronze  : Delta Lake on S3
  Silver  : AWS Glue (Spark) — SHA-256 masking here
  Gold    : dbt Core + Snowflake — Kimball Star Schema
  Orch    : Airflow standalone
  Quality : Great Expectations
  BI      : Power BI
  Query   : Databricks Serverless SQL (no Spark!)

TO RESUME:
  Baca PROJECT_STATUS.md → "Next Step When Resuming"
  Claude Code: "Baca CLAUDE.md dan PROJECT_STATUS.md. Start Phase 1 — BRD."
EOF

echo "✅ HOW_IT_WORKS.txt created"

# =============================================================================
# README.md
# =============================================================================

cat > README.md << 'EOF'
# Home Credit Risk Pipeline

Banking credit risk data engineering portfolio pipeline.

**Resume Entry:** Engineered scalable ingestion pipeline integrating 300k+ credit records
from 7 disparate source tables with GX data quality gating, SHA-256 PII masking,
and SCD Type 2 historical tracking.

## Tech Stack
| Layer | Tool |
|-------|------|
| Storage | AWS S3 + Delta Lake |
| Silver | AWS Glue (Spark) |
| Gold | dbt Core + Snowflake |
| Orchestration | Apache Airflow standalone |
| Quality | Great Expectations |
| BI | Power BI |

## Data Model — Kimball Star Schema
```
fact_loan_application    <- grain: 1 row = 1 application
fact_installment_payment <- grain: 1 row = 1 payment
fact_bureau_credit       <- grain: 1 row = 1 bureau record
dim_applicant            <- SCD Type 2
dim_loan_type            <- SCD Type 1
dim_credit_status        <- SCD Type 1
```

## Source Tables (7 files)
| File | Rows |
|------|------|
| application_train.csv | 307,511 |
| bureau.csv | 1,716,428 |
| bureau_balance.csv | 27,299,925 |
| previous_application.csv | 1,670,214 |
| installments_payments.csv | 13,605,401 |
| POS_CASH_balance.csv | 10,001,358 |
| credit_card_balance.csv | 3,840,312 |

## Pipeline Evidence
*(Updated selepas Phase 4b)*

### Airflow DAG
![airflow](docs/screenshots/airflow_dag_success.png)

### GX Validation Report
![gx](docs/screenshots/gx_validation_report.png)

### Snowflake Gold Layer
![snowflake](docs/screenshots/snowflake_gold_table.png)

### Slack Alert
![slack](docs/screenshots/slack_alert_success.png)

## Progress
| Phase | Status |
|-------|--------|
| 0 Setup | ✅ |
| 1 BRD | ⏳ |
| 2 DRD | ⏳ |
| 3 Architecture | ⏳ |
| 4 Code | ⏳ |
| 5 DQD + OPS | ⏳ |
EOF

echo "✅ README.md created"

# =============================================================================
# Git init + initial commit
# =============================================================================

git init

git add \
  .gitignore \
  .env.example \
  .mcp.json \
  docs/BRD.md \
  docs/DRD.md \
  docs/DATA_DICTIONARY.md \
  docs/DATA_MODEL.md \
  docs/PIPELINE_SPEC.md \
  docs/ARCHITECTURE.md \
  docs/DQD.md \
  docs/OPS_RUNBOOK.md \
  docs/ADR/ \
  airflow/dags/pipeline_dag.py \
  bronze/download_dataset.py \
  gold/profiles.yml \
  README.md \
  requirements.txt \
  infrastructure/credentials/SETUP_GUIDE.txt

git commit -m "[Phase 0] home-credit-risk-pipeline — Banking credit risk | Kimball | AWS"

# =============================================================================
# DONE
# =============================================================================

echo ""
echo "=========================================="
echo "✅ home-credit-risk-pipeline — scaffold complete!"
echo "=========================================="
echo ""
echo "Modelling : Kimball — Star Schema"
echo "Cloud     : AWS (S3 + Glue)"
echo "Databricks: Serverless SQL ONLY"
echo ""
echo "⚠️  BEFORE running download_dataset.py:"
echo "   Accept competition rules dulu:"
echo "   kaggle.com/competitions/home-credit-default-risk → Join"
echo ""
echo "Next steps:"
echo "  1. Letak CLAUDE.md dalam folder ni"
echo "  2. cp .env.example .env.dev"
echo "  3. Fill in KAGGLE_USERNAME + KAGGLE_KEY dalam .env.dev"
echo "  4. python bronze/download_dataset.py --env dev"
echo "  5. code ."
echo "  6. Claude Code: 'Baca CLAUDE.md dan PROJECT_STATUS.md. Start Phase 1 — BRD.'"
echo ""