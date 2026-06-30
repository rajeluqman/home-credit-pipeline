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
| Compute | `COMPUTE_WH` (dev target) | `dbt build` staging→snapshot→intermediate→mart | Monitor warehouse auto-suspend; dev/staging/prod schema split limits blast radius |

## Status
Phase 4b (cloud promote) is ⏳ per README.md "Phase Completion" — no real cloud cost data
exists yet. This log will get real numbers after the first cloud run; until then it documents
the allowance ceilings the design (ADR-003) was sized against.
