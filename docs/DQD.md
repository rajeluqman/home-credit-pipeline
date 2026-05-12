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
