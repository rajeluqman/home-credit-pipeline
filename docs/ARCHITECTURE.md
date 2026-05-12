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
