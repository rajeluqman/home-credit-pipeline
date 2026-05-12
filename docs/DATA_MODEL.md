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
