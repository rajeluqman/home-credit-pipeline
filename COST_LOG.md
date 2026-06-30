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

**2026-06-30 — Phase 2 scoping, observed-not-projected (this session):** live `boto3` checks
(not assumed) confirm **zero AWS Glue jobs exist in the account** (`glue.get_jobs()` → 0) and
**no Glue execution IAM role exists** (`iam.list_roles()` → 8 roles, none Glue-related) — so
**$0 Glue spend has occurred to date**, and a new IAM role must be created (owner-executed)
before any Glue DPU cost can be incurred at all. S3 storage: `home-credit-risk-dev-1` already
holds 2.6718 GB (mostly the already-landed full 58.4M-row raw CSVs); `home-credit-risk-staging`/
`home-credit-risk-prod` exist and are empty. See `INFRA_LIMITS_LOG.md` 2026-06-30 entries for the
full breakdown. Phase 2 execution has not started — this is a scoping pass only.

**2026-06-30 (continued) — IAM role created, Bronze promoted full-scale to staging, still $0 Glue
spend.** Owner created `glue_silver_execution_role` (verified live, matches drafted least-privilege
policy). Raw copied dev→staging (S3 server-side `copy_object`, no Kaggle re-download, negligible
request cost). Bronze ingestion for all 7 tables run full-scale against staging — **this used local
PySpark in the Codespace, not AWS Glue, so still $0 AWS Glue compute cost.** S3 footprint added:
0.6895 GB (`bronze/` in staging, Parquet/Delta-compressed from 2.6571 GB raw CSV). **Account-wide
S3 total now 6.0184 GB** vs. the 5 GB free-tier ceiling — owner explicit decision: "acknowledge and
continue," overage is cents/month at S3 Standard ap-southeast-1 rates, not worth pausing for.
**Real AWS Glue DPU spend has not started yet** — that begins with the next step (creating + running
the 5 real Glue Silver job definitions), which needs its own explicit go-ahead per the STOP-GATE
(first real compute-cost spend in the project), not assumed from this session's storage/IAM
progress.

**2026-06-30 (continued) — first real AWS Glue $ spend, owner go-ahead obtained.** 5 Glue job
definitions created (G.1X×2, Glue 4.0). 4 of 5 job runs completed (1 failed run during an IAM-scope
fix, 4 succeeded after): `glue_silver_application` 138 + 174 DPU-seconds, `glue_silver_previous_application`
154, `glue_silver_balance_tables` 179, `glue_silver_installments` 180 — **825 DPU-seconds total ≈
0.229 DPU-hours ≈ $0.10** at ~$0.44/DPU-hour Glue 4.0 standard ap-southeast-1 (estimate, not pulled
from the AWS Billing console). See `PROJECT_STATUS.md` "Real AWS Glue jobs created + 4/5 run" entry
for the per-job evidence table. Remaining job (`glue_silver_bureau`, the 27.3M-row bureau_balance
table) not yet run — separate go-ahead requested before incurring its cost, since it's the one
ADR-003's sizing math is actually about.

**2026-06-30 (continued) — `glue_silver_bureau` run, all 5 Glue jobs now complete.** Owner
go-ahead obtained; job SUCCEEDED, 96s, 192 DPU-seconds, no OOM on the 27.3M-row `bureau_balance`
table (real signal for `INFRA_LIMITS_LOG.md`'s previously-"Open" OOM-risk row, now Observed/
Resolved). **Final Phase-2-so-far Glue total: 1,017 DPU-seconds ≈ 0.2825 DPU-hours ≈ $0.124**
(estimate, ~$0.44/DPU-hour Glue 4.0 standard ap-southeast-1 — not pulled from AWS Billing console,
flag for a real billing-console reconciliation before Gate 2 sign-off). S3 footprint: staging
`silver/` 0.4493 GB; **account-wide S3 total 6.4677 GB** vs. 5 GB free tier (owner's standing
"acknowledge and continue" decision). Snowflake STAGING/PROD load (the other half of Gate 2's
first checklist item) not yet started — $0 Snowflake spend for Phase 2 so far.

**2026-06-30 (continued) — Silver(S3 staging)→Snowflake STAGING bridge built, manual COPY INTO
(not a second Snowpipe — owner decision, see `PROJECT_STATUS.md`).** No new persistent AWS
infrastructure: reused the existing `HOME_CREDIT_SILVER_INT` storage integration (widened
`STORAGE_ALLOWED_LOCATIONS` to add `s3://home-credit-risk-staging/silver/`, no new cross-account
trust — same `STORAGE_AWS_IAM_USER_ARN`/`STORAGE_AWS_EXTERNAL_ID`) and the existing
`snowflake_silver_loader` IAM role (owner widened its inline `snowflake_silver_read_policy` via
AWS Console to add read on `home-credit-risk-staging/silver/*`, same role, no new role). One new
`STAGE` (`HOME_CREDIT_RISK.STAGING.SILVER_STAGE`) and 4 new tables
(`HOME_CREDIT_RISK.STAGING.SILVER_APPLICATION`/`SILVER_BUREAU`/`SILVER_BUREAU_BALANCE`/
`SILVER_INSTALLMENTS`) — Snowflake metadata objects only, no AWS cost. Compute cost: 4 `COPY INTO`
statements on `HOME_CREDIT_WH` (X-Small), total wall time ≈20s for 14.5M rows / ~0.55 GB Parquet —
well under 1 minute of warehouse-active billing (X-Small auto-suspends at 60s idle per its
original creation config), **effectively $0 incremental Snowflake compute** (a fraction of the
warehouse's per-second minimum billing increment, not separately itemized). No SQS/Snowpipe
credit consumption — this bridge has no auto-ingest component, so no per-notification cost and no
ongoing accrual risk after this load. **Teardown surface added by this entry:** the `STAGE` +
widened `STORAGE_ALLOWED_LOCATIONS` + widened IAM policy — no `PIPE`, no S3 event notification, no
SQS, consistent with the design goal of not doubling ADR-004's still-open teardown debt.
