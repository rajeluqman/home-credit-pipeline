# ADR-004: Snowpipe Auto-Ingest — Silver (S3 Delta) → Snowflake Gold Bridge

Status: Proposed — @data-architect ✓ / @finops-agent ✓ / @scope-guardian ✓ (all APPROVE WITH
CONDITION); pending **owner** sign-off + the three binding scope-guardian conditions (teardown
executes post-Gate-1; `docs/ARCHITECTURE.md` stack-table edit lands with acceptance; IAM step
owner-executed). Does NOT move to Accepted until those hold.
Date  : 2026-06-30
Owner : Senior Data Engineer (build) · Scope Guardian (boundary) · Data Architect (data path)

## Context
`dbt_home_credit/models/sources.yml:4-9` defines the `silver` dbt source as native Snowflake
tables (`{{ source('silver', 'silver_application') }}` etc., `dbt_home_credit/models/staging/
stg_application.sql:28`), not S3 Delta paths. Silver output, however, is written by the Glue
jobs as Delta Lake on S3 (`s3://<bucket>/silver/silver_{table}/ingestion_date={date}/`,
`docs/ARCHITECTURE.md` lines 5-18). No loader code exists anywhere in this repo (`.py`/`.sql`/
`.yml`, verified by repo-wide grep, 2026-06-30) to bridge the two — `README.md:99` names
"Snowpipe / external stage" only as a one-line architecture diagram label, never built.

Live inspection of `HOME_CREDIT_RISK.DEV` (2026-06-30) found this bridge had previously been
filled by hand, out of band: `SILVER_APPLICATION`/`SILVER_BUREAU`/`SILVER_BUREAU_BALANCE`/
`SILVER_INSTALLMENTS` hold a stale 1,000/1,500/1,500/10,615-row dev sample (not this session's
real-Kaggle smart sample of 4,612/21,799/5,003/162,862 rows, per `PROJECT_STATUS.md`), with
downstream `dbt run` artifacts (`DEV_DEV.*`, `DEV_HOME_CREDIT_GOLD.*`) already built on top of
that stale data. This is unreproducible from any committed script — a real gap, not a
hypothetical one.

A 2026-06-30 governance cross-check (scope-guardian, Opus) reviewed three candidate bridge
mechanisms against `docs/ARCHITECTURE.md`, `docs/ADDENDUM-A_local-dev-smart-sampling.md`,
`PROJECT_STATUS.md`, and `tests/boundary_contract.py`, and **recommended against** full
auto-ingest Snowpipe in favor of a manual `COPY INTO` from an external stage — citing: (1)
`docs/ARCHITECTURE.md`'s locked stack table does not list Snowpipe/STORAGE INTEGRATION/SQS as
an admitted component; (2) `docs/ADDENDUM-A` §1 (line 21) and §6 (line 166) scope Phase-1
orchestration as "manual... no Airflow", and an S3-event-driven pipe that fires without a human
running a command violates that intent even though it is not literally Airflow; (3)
`PROJECT_STATUS.md` (lines 148-153) frames this session's prior S3 writes as a "one-time,
owner-approved exception... not a standing policy change" — persistent Snowpipe infrastructure
is the opposite of one-time. The cross-check did **not** find a conflict with CLAUDE.md's
"no new ingestion connectors beyond the Kaggle API" rule — that rule targets new *external*
data sources, not internal Silver→Gold data movement.

The owner reviewed this conflict and chose to proceed with full auto-ingest Snowpipe anyway,
specifically for portfolio reasons: the project's value includes demonstrating production-grade
pipeline automation capability, not only proving the Bronze→Silver→Gold logic once on a sample
(owner decision, 2026-06-30, given directly in response to this exact trade-off).

## Decision
Adopt Snowpipe auto-ingest (S3 `ObjectCreated` event notification → Snowflake-managed SQS queue
→ Snowflake auto-ingest `PIPE`) as the Silver→Snowflake bridge feeding `dbt_home_credit`'s
`silver` source tables, superseding the undocumented manual process that previously populated
`HOME_CREDIT_RISK.DEV.SILVER_*`.

This ADR formally amends:
- `docs/ARCHITECTURE.md`'s locked stack table (lines 5-18): add Snowpipe / STORAGE INTEGRATION /
  S3 event notification as an explicit, admitted Silver→Gold bridge component.
- `docs/ADDENDUM-A_local-dev-smart-sampling.md` §1 (line 21) and §6 (line 166): carve a named,
  narrow exception to Phase-1's "Orchestration: none (manual)" rule, scoped **only** to this one
  load step. Bronze ingestion, the Glue Silver jobs, and the `dbt run`/`dbt test` invocations
  themselves remain manual-triggered in Phase 1 — only the Silver(S3)→Snowflake table load
  auto-fires on new Delta file arrival.

## Why this over the simpler option
`docs/ADDENDUM-A`'s own Gate-1 proof goal ("Bronze→Silver→Gold runs end-to-end on the sample")
is satisfied identically by a manual `COPY INTO` from an external stage — same STORAGE
INTEGRATION mechanism, no new persistent AWS automation, zero Phase-boundary conflict. Choosing
the heavier auto-ingest path is **not** required by Gate 1's checklist; it is a deliberate
scope addition for portfolio demonstration value, made with the trade-offs above named and
accepted, not discovered after the fact.

## Consequences
(+) Demonstrates a real, production-shaped auto-ingest pattern (S3 event → Snowpipe), which a
    manual `COPY INTO` cannot show, for portfolio/interview purposes.
(+) Phase 2 (cloud, full 58.4M rows) inherits the same bridge unchanged — no rebuild needed when
    promoting past the sample.
(-) New **persistent** AWS infrastructure: one IAM role with a cross-account trust policy to
    Snowflake's `STORAGE_AWS_IAM_USER_ARN`, plus an S3 bucket event notification wired to a
    Snowflake-managed SQS queue. This did not exist before and must be tracked by
    @finops-agent (Snowpipe has its own credit-consumption model, distinct from warehouse
    compute) and periodically reviewed.
(-) `tests/boundary_contract.py` does not and will not catch this drift — Snowpipe is pure
    SQL/AWS-IAM configuration, no Python import, so none of ST1 (pyspark)/ST2 (databricks)/ST3
    (connector)/ST4 (dbt-type) fire on it. The CI gate stays green regardless; this ADR plus
    explicit sign-off is the only enforcement mechanism, not the automated contract.
(-) IAM role creation (cross-account trust) is a security-sensitive, hard-to-reverse action.
    Per the 2026-06-30 governance review, this step must be **human-executed** (the owner,
    walked through it), not run autonomously by an agent — the `home_credit` pipeline IAM user's
    write permissions were deliberately left unverified/untested for this reason.
(-) Re-ingestion on file overwrite (e.g., re-running the Glue job for the same
    `ingestion_date`) could fire a duplicate Snowpipe load with no human gate in between. The
    pipe itself **cannot** dedup at load time — its body is a plain `COPY INTO` and `MERGE` is
    not a legal pipe body (see the @data-architect condition below). `COPY INTO`'s default
    load-history (skip already-loaded files) reduces but does not eliminate the duplicate-row
    risk: a Delta MERGE rewriting files under new names defeats file-level dedup. The binding
    idempotency guarantee is therefore enforced **downstream in dbt** by the
    `QUALIFY ROW_NUMBER() ... = 1` dedup now in `stg_application.sql:34`, which collapses
    duplicate `SK_ID_CURR` rows before `dbt snapshot`, before this is trusted for anything
    beyond the Phase-1 sample proof.

**Teardown step (binding, @finops-agent condition):** once Gate 1's Gold run-evidence is
captured, the pipe must not stay armed indefinitely as a forgotten cost/drift surface. Run, in
order: `DROP PIPE <each pipe>;` → remove the S3 bucket event notification pointing at the
pipe's `notification_channel` SQS ARN → delete or disable the `snowflake_silver_loader` IAM role
(or at minimum revoke its trust policy). Log the teardown date in `COST_LOG.md`. Re-creating the
pipe for Phase 2 is a fresh, deliberate decision, not an assumption that Phase-1's pipe should
keep running unattended.

## Alternatives Rejected
- **Ad-hoc Python loader** (`write_pandas` from S3 Silver Delta straight into the existing
  Snowflake tables): rejected — one-off proof value only, no production-automation value, would
  need to be rebuilt entirely for Phase 2.
- **External Stage + manual `COPY INTO`** (scope-guardian's recommended option, 2026-06-30
  cross-check): fully compliant with Phase-1's manual-only framing, lowest risk, achieves an
  identical Gate-1 proof outcome. Rejected by the owner specifically because it does not
  demonstrate auto-ingest automation, which is part of this portfolio project's intended scope
  (owner decision 2026-06-30 — see Context).

## Sign-off required (not yet granted — implementation blocked until checked)
- [x] **@data-architect** — **APPROVE WITH CONDITION** (2026-06-30, Opus review). The snapshot
      chain has no dedup anywhere upstream of `dbt snapshot`: `stg_application.sql:28-29` selects
      from the source with only `WHERE SK_ID_CURR IS NOT NULL`, no `QUALIFY`/dedup;
      `int_applicant_attributes.sql` passes rows 1:1; `snap_applicant.sql` uses
      `strategy='check'`, `unique_key='applicant_id'`, which assumes one row per key per run. A
      re-fired Snowpipe load (file-level dedup defeated by a Delta MERGE rewriting files under
      new names — exactly this ADR's re-ingestion risk above) can land a duplicate physical row
      for the same `SK_ID_CURR`, which `dbt snapshot` can turn into **two `is_current=TRUE`
      rows** for one applicant — caught only after the fact by
      `assert_scd2_one_current_per_applicant.sql`, not prevented, and invisible to
      `tests/identity_contract.py` (static-only, never touches warehouse data) so CI stays green
      regardless. **CONDITION (binding, must ship with the implementation, not optional):** the
      `SILVER_APPLICATION` load must be idempotent on `SK_ID_CURR` before any snapshot run.
      **Technical correction (2026-06-30):** an earlier draft of this condition offered "(a)
      `MERGE INTO ... ON SK_ID_CURR` *inside the pipe*" as an option — that is **not buildable**.
      Snowflake's `CREATE PIPE ... AS <stmt>` accepts **only** a `COPY INTO <table>` statement as
      its body; `MERGE` is not a permitted pipe body (Snowflake docs, *CREATE PIPE* — "`copy_statement`
      ... COPY INTO <table> statement used to load data from queued files", independently verified
      2026-06-30). Therefore the pipe's `COPY INTO` **stays** (it is the only mechanism Snowflake
      allows), and raw landing into `SILVER_APPLICATION` happens **as-is, including possible
      duplicate `SK_ID_CURR` rows** on a re-fired load. The idempotency guarantee is instead
      enforced **downstream, in dbt**, by adding
      `QUALIFY ROW_NUMBER() OVER (PARTITION BY SK_ID_CURR ORDER BY ingestion_date DESC) = 1` to
      `dbt_home_credit/models/staging/stg_application.sql` (applied 2026-06-30 — see
      `stg_application.sql:34`), so at most one row per `SK_ID_CURR` reaches
      `int_applicant_attributes` → `snap_applicant`. Plain `COPY INTO` append into the raw table
      is accepted **only** because this downstream `QUALIFY` dedup now sits between it and
      `dbt snapshot`; **without that `QUALIFY`, plain append is rejected.**
- [x] **@scope-guardian** — **APPROVE WITH CONDITION** (2026-06-30, Opus review — final-text
      re-review, distinct from the earlier pre-document cross-check). All seven governing files
      read in full. Findings: (1) **Amendment scope is honest, not overreaching** — the Decision
      section (lines 49-56) confines the exception to the single Silver(S3)→Snowflake load step
      and explicitly preserves Bronze, Glue Silver, and `dbt run`/`dbt test` as still
      manual-triggered, consistent with `docs/ADDENDUM-A_local-dev-smart-sampling.md:21` ("Manual
      / Makefile — no Airflow") and `:166` ("Orchestration: none (manual) until Phase 3"); no
      stalking-horse for general auto-orchestration. (2) **Not a new ingestion connector** —
      `tests/boundary_contract.py:52-54` (ST3) only denies `fivetran`/`airbyte` imports; Snowpipe
      moves data *internally* between already-admitted stack components (`docs/ARCHITECTURE.md:7,10`
      — S3 + Snowflake), so CLAUDE.md's "no new ingestion connectors beyond the Kaggle API" rule
      (`CLAUDE.md:77-79`) does not fire — the ADR's reading (lines 34-36) matches the rule's
      intent. (3) **Boundary-contract blind spot accurately disclosed** — verified ST1-ST4
      (`tests/boundary_contract.py:47-54,93-102`) are static-import/profile-only and cannot see
      `CREATE PIPE`/IAM/S3-event config; ADR lines 76-79 state this precisely, not as spin. (4)
      **Dedup fix is real and present** — `dbt_home_credit/models/staging/stg_application.sql:34`
      contains the `QUALIFY ROW_NUMBER()... = 1` guard with explanatory comment (`:30-33`); the
      MERGE-inside-pipe error was correctly caught and removed. **CONDITIONS (binding, all three
      must hold before Status moves Proposed → Accepted):** (a) the teardown step (lines 90-96 /
      Consequences) must **actually execute** post-Gate-1 — not slip into a second "temporary"
      infra item that becomes permanent the way the original undocumented manual Silver loader did
      (lines 16-22 are evidence that exact failure mode already recurred once); (b) the
      `docs/ARCHITECTURE.md` stack-table edit (lines 5-18) that this ADR claims to make is **not
      yet landed** — it must land in the same commit/PR as ADR acceptance, or doc and reality stay
      out of sync (`tests/doc_reference_contract.py` won't catch stack-table incompleteness); (c)
      IAM/cross-account-trust creation stays **owner-executed** (lines 80-83) — any
      agent-autonomous execution of that step is an independent veto trigger. With (a)-(c)
      honored, this is a disclosed, bounded, single-step exception — within scope, not creep.
- [x] **@finops-agent** — **APPROVE WITH CONDITION** (2026-06-30, Opus review). Cost magnitude at
      sample scale is negligible (cents — ~0.06 credits/1,000 file notifications plus a few
      cents of serverless load compute across the 4,612-applicant sample's handful of Silver
      Delta files; AWS-side IAM role/SQS/event-notification add no meaningful cost). The real
      risk is **persistent set-and-forget accrual** — the pipe stays armed after Gate 1 closes
      and silently re-fires (burning credits, no human gate) on any future write to
      `s3://<bucket>/silver/...`. **CONDITION (binding):** (1) `COST_LOG.md` Snowflake section
      updated with a Snowpipe line item (done — see `COST_LOG.md`); (2) a documented teardown
      step added to this ADR's Consequences (done — see above) and actually executed once Gate
      1's run-evidence is captured, not left running indefinitely.
- [ ] **Owner** — executes the AWS IAM role creation and Snowflake `STORAGE INTEGRATION`/`PIPE`
      setup personally (human-execution-only per the security guardrail above); agent role is
      teaching/walkthrough only for this step.
