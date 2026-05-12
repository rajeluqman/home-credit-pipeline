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
