# home-credit-risk-pipeline

End-to-end credit risk profiling pipeline — Home Credit Default Risk dataset (307,511 loan applications across 7 source tables).

Built as a banking data engineering portfolio project demonstrating **Kimball Star Schema** modelling across a full medallion architecture: Bronze → Silver → Gold → BI, with PII masking (SHA-256), SCD Type 2 historical tracking, and automated data quality gating.

---

## Problem Statement

| Problem | Solution |
|---------|----------|
| Integrate 300k+ credit applications from 7 disparate source tables with schema alignment | Bronze ingestion — all 7 CSVs unified under Delta Lake with `ingestion_ts` + `ingestion_date` |
| Mask sensitive applicant fields (DAYS_BIRTH, DAYS_EMPLOYED) for GDPR compliance | Silver Glue jobs — SHA-256 after 365243→NULL substitution (DI-002) |
| Track applicant demographic changes over time for compliance audit trail | `dim_applicant` — SCD Type 2 via dbt snapshot (`start_date`, `end_date`, `is_current`) |
| Quantify credit default risk and bureau credit exposure per applicant | `fact_loan_application` + `fact_bureau_credit` — KPI-01 to KPI-05 |

---

## Data Model — Kimball Star Schema

| Table | Type | Grain | Why |
|-------|------|-------|-----|
| `fact_loan_application` | Fact | 1 row = 1 loan application (SK_ID_CURR) | Central fact — default rate, income ratios, credit amounts |
| `fact_bureau_credit` | Fact | 1 row = 1 bureau credit record (SK_ID_BUREAU) | External bureau exposure per applicant |
| `fact_installment_payment` | Fact | 1 row = 1 installment payment (SK_ID_PREV + NUM) | Payment punctuality — days early/late |
| `dim_applicant` | Dimension | SCD Type 2 — 1 row per version | Historical tracking — income type, education, family status changes |
| `dim_loan_type` | Dimension | SCD Type 1 — 1 row per contract type | Static lookup — Cash loans / Revolving loans |
| `dim_credit_status` | Dimension | SCD Type 1 — 1 row per CREDIT_ACTIVE value | Static lookup — Active / Closed / Bad debt / Sold |

**Paradigm:** Kimball chosen over OBT — bureau_balance (27M rows) + installments (13M rows) as OBT nested arrays → AWS Glue OOM risk on free tier. Kimball joins deferred to Snowflake compute. Documented in `docs/ADR/ADR-001-kimball-star-schema.md`.

---

## Stack

| Layer | Tool | Note |
|-------|------|------|
| Dataset | Home Credit Default Risk (Kaggle Competition API) | 7 CSV files — 300k–27M rows each |
| Ingestion | Python + boto3 | CSV → S3 landing → Delta Lake Bronze |
| Storage | AWS S3 | Free tier 5GB — landing + Bronze + Silver |
| Bronze | Delta Lake on S3 | ACID, time travel, raw schema + metadata cols |
| Silver | AWS Glue (PySpark) | 5 Glue jobs — G.1X × 2 workers, Glue 4.0 |
| Gold | dbt Core + Snowflake | staging → intermediate → mart (3-layer + snapshots) |
| Orchestration | Apache Airflow standalone | localhost:8080, 3 chained DAGs |
| Quality | Great Expectations | `bronze_suite` + `silver_suite` — gate before each layer |
| Alerting | Slack webhook | DAG pass/fail + pipeline health |
| BI | Power BI | Gold consumer — credit risk dashboard |
| Analytics | Databricks Serverless SQL | Query layer ONLY — no Spark jobs |

---

## Architecture

```
Home Credit CSVs (7 tables, 300k–27M rows each)
    ↓ Python + boto3 (bronze/download_dataset.py)
AWS S3 Landing Zone  s3://{bucket}/landing/
    ↓ Airflow: bronze_ingestion_dag — ingest_bronze.py × 7 tables (parallel)
Bronze — Delta Lake on S3  s3://{bucket}/bronze/{table}/ingestion_date={date}/
    │  Raw schema + ingestion_ts + ingestion_date | GX: bronze_suite
    ↓ Airflow: silver_transforms_dag — 5 AWS Glue PySpark jobs
Silver — Delta Lake on S3  s3://{bucket}/silver/silver_{table}/ingestion_date={date}/
    │  PII masked | XNA→NULL | 365243→NULL | Deduped | Delta MERGE upsert
    │  GX: silver_suite (PII check, dedup, RI orphan check)
    ↓ Snowpipe / external stage
Snowflake  HOME_CREDIT_RISK  (schemas: DEV / STAGING / PROD)
    ↓ Airflow: gold_dbt_dag — dbt Core
Gold — Kimball Star Schema
    staging → snap_applicant (SCD2) → intermediate → mart
    ↓
Power BI Credit Risk Dashboard | Databricks Serverless SQL
```

---

## Key KPIs

| KPI | Formula | dbt Location |
|-----|---------|--------------|
| KPI-01: Default rate (%) | `COUNT(target=1) / COUNT(*) × 100` | `fact_loan_application` |
| KPI-02: Bureau exposure per applicant | `SUM(amt_credit_sum) GROUP BY applicant` | `fact_bureau_credit` |
| KPI-03: Overdue rate (%) | `COUNT(credit_day_overdue > 0) / COUNT(*)` | `fact_bureau_credit` |
| KPI-04: Income-to-credit ratio | `amt_income_total / NULLIF(amt_credit, 0)` | `fact_loan_application` |
| KPI-05: Payment punctuality | `AVG(days_payment_diff)` — positive = late, negative = early | `fact_installment_payment` |

---

## SCD Type 2 — dim_applicant

```
dbt snapshot: snap_applicant.sql
  strategy   : check
  unique_key : applicant_id  (= SK_ID_CURR)
  check_cols : [name_income_type, name_education_type, name_family_status, cnt_children]

mart alias: dim_applicant.sql
  dbt_valid_from → start_date
  dbt_valid_to   → end_date
  CASE WHEN dbt_valid_to IS NULL THEN TRUE ELSE FALSE END → is_current

dbt test: assert_scd2_one_current_per_applicant.sql
  → exactly 1 is_current=TRUE per applicant_id at all times
```

---

## PII Masking Strategy

```
Columns : DAYS_BIRTH, DAYS_EMPLOYED
Method  : SHA-256 — hashlib.sha256(str(value).encode()).hexdigest()
Order   : 365243 → NULL first (DI-002), THEN SHA-256 (never hash the sentinel value)
Applied : Bronze → Silver transform (Glue job, before Delta write)
GX gate : DAYS_BIRTH_MASKED not null | DAYS_EMPLOYED_MASKED not in sha256('365243')
```

---

## Source Tables (7 files)

| File | Rows | Bronze → Silver |
|------|------|-----------------|
| application_train.csv | 307,511 | 23 cols kept, PII masked, XNA→NULL, dedup SK_ID_CURR |
| bureau.csv | 1,716,428 | 14 cols, dedup SK_ID_BUREAU |
| bureau_balance.csv | 27,299,925 | Filter MONTHS_BALANCE=0 → ~1.7M rows in Silver |
| previous_application.csv | 1,670,214 | 8 cols, no dedup (Silver only — Gold deferred BR-10) |
| installments_payments.csv | 13,605,401 | 8 cols, dedup on (SK_ID_PREV, NUM_INSTALMENT_NUMBER) |
| POS_CASH_balance.csv | 10,001,358 | 8 cols, append mode (no natural dedup key) |
| credit_card_balance.csv | 3,840,312 | 9 cols, append mode (Gold deferred BR-11) |

---

## Project Structure

```
home-credit-pipeline/
├── bronze/
│   ├── download_dataset.py             # Kaggle Competition API → S3 (env-aware)
│   ├── ingest_bronze.py                # CSV → Delta Lake, PK quarantine, metadata cols
│   └── generate_dev_data.py            # Synthetic dev data — exact schema match
├── silver/
│   └── transforms.py                   # Pandas transforms — mirrors Glue logic (local testing)
├── glue/
│   ├── glue_silver_application.py      # PySpark — DI-001, DI-002, SHA-256, MERGE
│   ├── glue_silver_bureau.py           # PySpark — bureau + bureau_balance (MONTHS_BALANCE=0)
│   ├── glue_silver_previous_application.py
│   ├── glue_silver_installments.py
│   └── glue_silver_balance_tables.py   # POS cash + credit card — append mode
├── dbt_home_credit/
│   ├── dbt_project.yml
│   ├── profiles.yml                    # 3 Snowflake targets: dev / staging / prod
│   ├── sources.yml
│   ├── models/
│   │   ├── staging/                    # stg_application, stg_bureau, stg_bureau_balance, stg_installments
│   │   ├── intermediate/               # int_applicant_attributes, int_bureau_with_balance, int_installment_payments
│   │   └── mart/                       # fact_loan_application, fact_bureau_credit, fact_installment_payment
│   │                                   # dim_applicant (SCD2), dim_loan_type, dim_credit_status
│   ├── snapshots/
│   │   └── snap_applicant.sql          # SCD Type 2 — strategy: check, 4 tracked cols
│   ├── tests/
│   │   ├── assert_scd2_one_current_per_applicant.sql
│   │   ├── assert_fk_loan_application_applicant.sql
│   │   └── assert_fk_bureau_credit_applicant.sql
│   └── macros/
│       └── generate_surrogate_key.sql
├── airflow/dags/
│   ├── bronze_ingestion_dag.py         # 7 ingest tasks parallel → GX → trigger Silver
│   ├── silver_transforms_dag.py        # 5 GlueJobOperator → GX → trigger Gold
│   └── gold_dbt_dag.py                 # staging → snapshot → intermediate → mart → test → Slack
├── gx/
│   ├── great_expectations.yml
│   ├── run_bronze_suite.py             # Row count > 0, PK NOT NULL (WARN — pipeline continues)
│   └── run_silver_suite.py             # PII, dedup, RI checks (FAIL → DAG stops)
├── tests/unit/
│   ├── test_bronze_ingest.py           # 5 tests — quarantine, parquet write, metadata cols
│   └── test_silver_transforms.py       # 17 tests — DI-001, DI-002, SHA-256, dedup per table
├── docs/
│   ├── ADR/ADR-001-kimball-star-schema.md
│   ├── BRD.md | DRD.md | DATA_MODEL.md | ARCHITECTURE.md | PIPELINE_SPEC.md
│   └── DATA_DICTIONARY.md
├── setup.sh
└── requirements.txt
```

---

## Phase Completion

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Setup + scaffold | ✅ |
| 1 | BRD — 6 Must Have, 5 KPI formulas, 6 business rules | ✅ Signed Off 2026-05-12 |
| 2 | DRD + Data Dictionary + Data Model (conceptual) | ✅ Signed Off 2026-05-12 |
| 3 | Architecture + PIPELINE_SPEC + Data Model (logical) | ✅ Signed Off 2026-05-12 |
| 4a | Code — local dev (22/22 pytest, all deliverables built) | 🔶 In Progress |
| 4b | Cloud promote — Glue staging run, dbt on full dataset | ⏳ |
| 5 | DQD + OPS Runbook | ⏳ |

---

## Running Locally (Dev — 1,000 rows)

```bash
# Setup
bash setup.sh
cp .env.example .env.dev
# Fill in: KAGGLE_USERNAME, KAGGLE_KEY, SNOWFLAKE_*, AWS_*

# Accept competition rules first: kaggle.com/competitions/home-credit-default-risk/rules
python bronze/download_dataset.py --env dev

# Bronze ingestion (local parquet — no AWS needed for dev)
python bronze/ingest_bronze.py --table application_train --env dev

# Unit tests
pytest tests/unit/ -v

# dbt (requires Silver data loaded to Snowflake DEV schema)
dbt run --profiles-dir dbt_home_credit --project-dir dbt_home_credit --target dev
dbt test --profiles-dir dbt_home_credit --project-dir dbt_home_credit --target dev
```

---

## Pipeline Evidence
*(Updated after Phase 4b cloud promote)*

| Step | Result |
|------|--------|
| Bronze — 7 tables ingested | ⏳ Phase 4b |
| Silver — 5 Glue jobs | ⏳ Phase 4b |
| Snowflake load | ⏳ Phase 4b |
| dbt run | ⏳ Phase 4b |
| dbt test | ⏳ Phase 4b |
| GX bronze_suite | ⏳ Phase 4b |
| GX silver_suite | ⏳ Phase 4b |

---

*Portfolio — Raja Ahmad Luqman | Analytics & Data Engineering*
