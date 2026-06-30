# Cost Log — Home Credit Risk Pipeline

> Estimates only. Never commit real account-linked $ figures or billing exports.

## AWS Free Tier
| Resource | Free-tier allowance | This repo's usage pattern | Risk |
|---|---|---|---|
| S3 storage | 5 GB | Landing + Bronze + Silver copies of 7 CSVs (largest: bureau_balance.csv ~27M rows) | Tight — dev-sample runs use `DEV_SAMPLE_ROWS=1000` to stay under cap; full-dataset cloud promote (Phase 4b) needs a real size check before running |
| Glue DPU-hours | 1M free DPU-seconds/month (first 2 months, then pay-per-use) | 5 jobs × G.1X × 2 workers | See ADR-003 sizing math — 32GB executor ceiling is the binding constraint, not DPU-hours, for the 27M-row bureau_balance job |

## Snowflake
| Resource | Tier | Usage | Risk |
|---|---|---|---|
| Compute | `HOME_CREDIT_WH` (dev target, X-Small, auto-suspend 60s) — dedicated warehouse created 2026-06-30, replaces shared `COMPUTE_WH` | `dbt build` staging→snapshot→intermediate→mart | Monitor warehouse auto-suspend; dev/staging/prod schema split limits blast radius |
| Snowpipe auto-ingest | Serverless — ~0.06 credits/1,000 file notifications + load compute-seconds | Silver(S3 Delta)→Snowflake bridge for `SILVER_*` tables (ADR-004, Proposed) | Cents at sample scale (~tens of files across 4 tables for the 4,612-applicant sample) — **not** the concern. Real risk: **persistent, set-and-forget** — pipe stays armed after Gate 1 closes; any future write to `s3://<bucket>/silver/...` (re-run Glue job, unrelated upload) silently re-fires and burns credits with no human gate. @finops-agent condition (2026-06-30): requires a documented teardown step (DROP PIPE + remove S3 event notification + delete/disable IAM role) once Gate-1 evidence is captured, plus monthly review until then. |

## Status
Phase 4b (cloud promote) is ⏳ per README.md "Phase Completion" — no real cloud cost data
exists yet. This log will get real numbers after the first cloud run; until then it documents
the allowance ceilings the design (ADR-003) was sized against.
