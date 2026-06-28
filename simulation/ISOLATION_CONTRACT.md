# Isolation Contract — Home Credit Simulation Lab

> **Purpose:** guarantee the sim lab can never corrupt the real Glue/dbt/Snowflake pipeline.
> This is what makes deliberate fault-injection and optimization drills safe — break the sim
> all you want, `main` is untouchable. Enforced by `python simulation/check_isolation.py`
> (deterministic, no AWS/Snowflake connection needed). Run it before every sim session AND
> before committing any sim work. PASS required.

Ported from `creative_intelligence_lab`'s simulation isolation contract (pipeline-retrofit
effort), retargeted to this repo's real stack: Snowflake schemas instead of a single DuckDB
catalog, S3 prefixes instead of CIL's staging-bucket convention.

## The rules

**R1 — Own S3 prefix.** Everything the sim reads or writes lives under
`s3://<bucket>/sim/<scenario>/...`. The sim must never reference the real `landing/`,
`bronze/`, `silver/` paths. *Guard:* every `s3://` literal in a sim file must contain `/sim/`.

**R2 — Own Snowflake schema.** The sim has its own dbt project at `simulation/sim_dbt/`
(project name `sim_home_credit`, profile target `sim`, schema `HOME_CREDIT_RISK_SIM` — never
`DEV`/`STAGING`/`PROD`). *Guard:* sim `dbt_project.yml` `name` != the real
`dbt_home_credit/dbt_project.yml` `name`.

**R3 — No cross-refs.** No sim model may `ref()` a real `dbt_home_credit/models/**` model, and
no sim file may read a real Glue job output by path. The sim's "legacy source" is synthetic
dev data (reuse `bronze/generate_dev_data.py`'s pattern, pointed at sim paths only). *Guard:*
no `ref('<real model>')` appears in any `simulation/**/*.sql`.

**R4 — Real tree is read-only.** `glue/`, `dbt_home_credit/`, `docs/`, `airflow/dags/`, `tests/`
are reference-only for the sim — read them to learn the patterns, never edit them from a sim task.

**R5 — Faults stay in the lab, and reset is total.** Fault injection happens only inside
`simulation/`. The clean state must be fully rebuildable from sim seeds (`faults/reset.py` =
re-seed + re-build sim), never hand-patched.

## What the guard checks
`check_isolation.py` statically enforces R1, R2, R3. R4/R5 stay partly human discipline.

## If a rule and a task conflict
STOP and surface it (same as the main project's STOP-GATE in CLAUDE.md). Do not point the sim
at the real Snowflake schema or S3 lake "just this once."
