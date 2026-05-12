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
