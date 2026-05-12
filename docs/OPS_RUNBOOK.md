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
