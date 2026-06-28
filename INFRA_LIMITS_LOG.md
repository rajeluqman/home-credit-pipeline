# Infra Limits Log — Home Credit Risk Pipeline

> Owner: @infra-reality-agent. Every entry is an OBSERVED or PROJECTED ceiling with the actual
> number, not a guess. Cross-check any resourcing proposal against this before approving.

| Date | Resource | Ceiling | Source | Status |
|---|---|---|---|---|
| 2026-06-28 | Glue executor memory | G.1X × 2 workers ≈ 32 GB total | README.md "Stack" table + AWS Glue G.1X spec (1 DPU = 4 vCPU/16GB) | Projected — sizing math in `docs/ADR/ADR-003-kimball-over-obt-sizing.md`, not yet measured against a real cloud run |
| 2026-06-28 | S3 free-tier storage | 5 GB | `.env.example` `S3_BUCKET_DEV` etc. comment | Tight against Landing+Bronze+Silver copies of 7 CSVs at full scale (58.4M rows); dev mode uses 1,000-row samples to stay under it |
| — | Glue OOM risk, full-scale `bureau_balance` (27M rows) join | Unconfirmed | Phase 4b cloud promote (⏳ per README.md "Phase Completion") | **Open — first real signal will come from the Phase 4b run, not before** |

## How to add an entry
Only add a row with a REAL observed number (a Glue job's CloudWatch metrics, an actual S3
bucket size, a Snowflake warehouse credit report) or a clearly-labeled "Projected" estimate
with its source formula shown. Never round up a guess into looking like a measurement.
