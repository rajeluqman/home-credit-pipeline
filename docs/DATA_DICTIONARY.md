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
