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
| 1 BRD | ✅ |
| 2 DRD | ⏳ |
| 3 Architecture | ⏳ |
| 4 Code | ⏳ |
| 5 DQD + OPS | ⏳ |
