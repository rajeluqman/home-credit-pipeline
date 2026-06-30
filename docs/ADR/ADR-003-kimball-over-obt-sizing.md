# ADR-003: Kimball-over-OBT Sizing Math (free-tier Glue OOM risk)

Status: Accepted
Date  : 2026-06-28 (backfilled during pipeline-retrofit governance pass — sizing math is
        derived from real row counts in README.md/docs/DATA_DICTIONARY.md; the OOM-risk
        conclusion mirrors ADR-001's existing one-line note, expanded here with the actual
        numbers so the decision is checkable, not asserted)
Owner : Data Architect + Infra Reality Agent

## Context
ADR-001 already locked Kimball star schema over One-Big-Table (OBT), citing
"bureau_balance (27M rows) + installments (13M rows) as OBT nested arrays → AWS Glue OOM risk
on free tier" in one line. This ADR shows the arithmetic behind that one line so a future
"why not OBT, it'd save joins" re-litigation has numbers to check against, not just a citation.

## The sizing math
Glue job config (README.md "Stack" table): **G.1X workers × 2**. Per AWS Glue docs, G.1X = 1
DPU = 4 vCPU / 16 GB memory per worker → **2 workers × 16 GB ≈ 32 GB total executor memory**
on the free-tier job configuration this repo uses.

OBT-as-nested-array would require, per `SK_ID_CURR`, collecting:
- `bureau_balance.csv`: 27,299,925 rows total, keyed via `bureau.csv` (1,716,428 rows) →
  averages ~16 balance-history rows per bureau record, themselves fan-out per applicant
- `installments_payments.csv`: 13,605,401 rows, keyed via `previous_application.csv`
  (1,670,214 rows) → averages ~8 installment rows per previous-application record

Collecting these as nested array/struct columns on a 307,511-row `application_train.csv` base
means the **widest rows** (applicants with many bureau records, each with many balance-history
entries) carry a multiplicatively larger in-memory footprint than the table-average suggests —
a small number of "fat" applicant rows can dominate a single Spark partition's memory, which is
exactly the failure mode 32 GB of free-tier executor memory has little headroom against, since
Glue's catalog/shuffle/serde overhead already consumes a meaningful share of that 32 GB before
any nested-array memory ballooning. Kimball avoids this because each table caps its grain (1 row
= 1 bureau record / 1 installment record) — no row's memory footprint depends on a *fan-out*,
only deferred Snowflake-side joins do.

## Decision
Kimball star schema (re-affirmed from ADR-001). Joins deferred to Snowflake compute, which has
no comparable free-tier executor-memory ceiling for the join step (warehouse-scale joins, not
in-Glue-executor-memory joins).

## Consequences
(+) Each Silver Glue job (`glue/glue_silver_bureau.py`, `glue/glue_silver_installments.py`,
    etc.) processes one flat table at a time — bounded memory per job, independent of any other
    table's fan-out
(+) Snowflake absorbs the join cost in Gold (`dbt_home_credit/models/intermediate/
    int_bureau_with_balance.sql`, `int_installment_payments.sql`) where compute scales
    independently of the 32 GB Glue ceiling
(-) More join steps in dbt vs a single denormalized OBT query
(-) This sizing math is a worst-case bound, not a measured Glue OOM (Phase 4b cloud-promote
    run, still ⏳ per README.md "Phase Completion", will confirm or revise this estimate)

## Alternatives Rejected
- OBT with nested arrays in Glue: rejected per the sizing math above.
- Larger Glue worker type (G.2X/G.4X) to make OBT viable: rejected — outside the stated
  AWS free-tier budget (`docs/ARCHITECTURE.md`); revisit only with @finops-agent sign-off if
  the project moves off free tier.
