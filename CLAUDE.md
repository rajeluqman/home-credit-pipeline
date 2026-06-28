# Home Credit Risk Pipeline — AI Context

> Auto-loaded by Claude Code every session. Governance framework ported from
> `creative_intelligence_lab` (CIL) per the pipeline-retrofit effort — see
> `docs/RETROFIT_NOTE.md` for provenance. Stack is UNCHANGED by the retrofit: this file
> documents the repo as it actually is, not a CIL stack swap.

## 🛑 STOP-GATE — read before ANY model/schema/identity work
This repo is governed. Before you edit a Glue job, a dbt mart model, a snapshot, or a
seed/source — or before you "proceed" past an identity/grain question — you MUST:
1. **Open the governing doc first.** Grain/star schema → ADR-001 + `docs/DATA_MODEL.md`.
   PII masking order → ADR-002. Kimball-over-OBT sizing → ADR-003. Stack boundary (Glue-only
   Spark, Databricks query-only) → `docs/ARCHITECTURE.md` + `tests/boundary_contract.py`.
2. **Validate identity BEFORE building downstream.** `dim_applicant` is SCD Type 2 keyed on
   `SK_ID_CURR` (`applicant_id`) — exactly one `is_current = TRUE` row per applicant at all
   times (`dbt_home_credit/tests/assert_scd2_one_current_per_applicant.sql`). Run
   `python tests/identity_contract.py` and `python tests/boundary_contract.py` before calling
   any mart/Glue change done — these are the binding checks, not your judgement.
3. **If a rule and the request conflict, STOP and surface it** — do not silently proceed.
   Mixed-grain dimension, Spark outside Glue, Databricks beyond Serverless SQL query, PII
   masked in the wrong order (DI-002: sentinel→NULL must happen BEFORE SHA-256) → name it,
   cite the doc, and ask @data-architect / @scope-guardian before writing code.

Enforced three ways: this prompt (soft), `.claude/hooks/governance_guard.py` (blocks edits to
governed files without a context nudge), and CI (`tests/identity_contract.py` +
`tests/boundary_contract.py` + `tests/doc_reference_contract.py`, blocks the PR).

## 🔁 ANTI-SHORTCUT PROTOCOL — read-before-touch, reconcile-before-done
1. **Read-before-touch** — never edit or assert about a file from memory; read it THIS turn.
2. **Enumerate, don't sample** — for "all N tables/jobs" tasks, get N from `ls`/`grep` BEFORE
   acting (7 source tables, 5 Glue jobs, 3 chained Airflow DAGs — verify the count, don't
   recall it).
3. **Reconcile-before-done** — before saying done/fixed/green, restate the request as a
   numbered checklist with `file:line` evidence per item. No evidence = "unverified".
4. **Tag assumptions** — any unchecked load-bearing claim is marked "(unverified)"; any
   reconstructed rationale (no contemporaneous deliberation) is marked
   "(reconstructed — owner confirm)".

The machine half: `tests/doc_reference_contract.py` proves every model/path a doc references
actually exists. `scripts/gen_repo_map.py` generates `architecture/REPO_MAP.md` — a pointer
index, not a cache; it tells you which file to open, then you read that file fresh.

## Project Overview
**Domain**: Consumer credit risk (banking).
**Problem**: Profile credit default risk across 307,511 loan applications + 6 related bureau/
installment/balance tables (≈58.4M rows total across the 7 source CSVs — see "Source Tables"
below), built as a Kimball star schema with PII masking and SCD2 historical tracking.
**Purpose**: Data Engineering portfolio project (single-dev, Raja Ahmad Luqman).

## Stack (locked — unchanged by this retrofit)
| Layer | Storage | Compute / engine | Notes |
|-------|---------|------------------|-------|
| Source | Kaggle Competition API (`home-credit-default-risk`) | `bronze/download_dataset.py` | 7 CSVs, 300k–27M rows each |
| Landing/Bronze | S3, Delta Lake | `bronze/ingest_bronze.py` | ACID, time travel, `ingestion_ts`/`ingestion_date` |
| Silver | S3, Delta Lake | **AWS Glue (PySpark)** — `glue/glue_silver_*.py` (5 jobs, G.1X×2, Glue 4.0) | PII mask (DI-002), XNA→NULL, dedup, MERGE upsert |
| Gold/marts | Snowflake (`HOME_CREDIT_RISK` DB) | dbt Core, `dbt_home_credit/models/{staging,intermediate,mart}` | Kimball star, SCD2 snapshot |
| Quality | Great Expectations | `gx/run_bronze_suite.py` (WARN), `gx/run_silver_suite.py` (FAIL) | per-layer gates |
| Orchestration | — | Apache Airflow standalone, `airflow/dags/` (3 chained DAGs) | localhost:8080 |
| Alerting | Slack webhook | `airflow/dags/gold_dbt_dag.py` (`SlackWebhookOperator` / curl `BashOperator`) | DAG pass/fail |
| Serving (query-only) | reads Gold Snowflake | **Databricks Serverless SQL** | query layer ONLY — no PySpark, no Classic Compute |
| BI | reads Gold Snowflake | Power BI | dashboard consumer |

⚠️ Stack boundary: **Spark only inside AWS Glue** (no standalone PySpark elsewhere) — Databricks
is admitted **query-only via Serverless SQL**, never as a compute/transform engine
(`tests/boundary_contract.py` ST1/ST-DBX). No MinIO, no dedicated vector DB, no RAG/dashboard
framework in pipeline code (this repo has no such use case to begin with).

## Architecture of Record
`docs/` — BRD.md, DRD.md, DATA_MODEL.md, ARCHITECTURE.md, PIPELINE_SPEC.md, DATA_DICTIONARY.md,
DQD.md, OPS_RUNBOOK.md, `ADR/` (ADR-001 Kimball-over-OBT paradigm, ADR-002 PII-mask-order,
ADR-003 Kimball-over-OBT sizing math). `architecture/REPO_MAP.md` (generated, see above).

**Identity key**: `SK_ID_CURR` (aliased `applicant_id`) — SCD Type 2 via `dbt snapshot` (`strategy:
check`, tracked cols: `name_income_type`, `name_education_type`, `name_family_status`,
`cnt_children`). Bureau/installment facts key on `SK_ID_BUREAU` / `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)`.

**Governance gate**: @data-architect holds veto on grain/model changes (Kimball star locked,
ADR-001); @scope-guardian holds veto on stack/scope creep (no Spark outside Glue, no Databricks
compute, no new ingestion connectors beyond the Kaggle API).

## Source Tables (7 files, ≈58.4M rows total — reconciles resume "58M rows" claim)
| File | Rows |
|------|------|
| application_train.csv | 307,511 |
| bureau.csv | 1,716,428 |
| bureau_balance.csv | 27,299,925 |
| previous_application.csv | 1,670,214 |
| installments_payments.csv | 13,605,401 |
| POS_CASH_balance.csv | 10,001,358 |
| credit_card_balance.csv | 3,840,312 |

## Cabinet (11 agents) — see `.claude/agents/`
**Veto holders**: @data-architect (grain/model) · @scope-guardian (stack/scope).
**Build**: @senior-data-engineer (dbt+Glue+orchestration) · @data-quality-steward (GX suites) ·
@product-owner (BRD/KPIs) · @business-analyst (DRD + resume-claim reconciliation) ·
@data-platform-engineer (Airflow/AWS infra) · @documentation-sherpa (docs/ADR upkeep) ·
@finops-agent (AWS free-tier + Snowflake credit watch) · @infra-reality-agent (Glue OOM risk,
free-tier limits — `INFRA_LIMITS_LOG.md`).
**Teaching**: @cikgu (English-first, mental-model → ETL use-case → production bug → debug →
syntax LAST) — NOT a build agent; runs `learning/CURRICULUM.md` drills on `drill/*` branches,
never `main`.

## What NOT to commit
`.env*`, `data/`, `*.parquet` (except via dbt build output paths already gitignored),
raw Kaggle CSVs, `COST_LOG.md` if it ever contains real account IDs — keep cost figures
estimate-only.

## Token Discipline
1. Checkpoint first: read `PROJECT_STATUS.md` "▶ RESUME HERE" before reading code.
2. Use `architecture/REPO_MAP.md` instead of re-grepping the whole repo for "where is X".
3. Read only files in the current module — max ~3 files/turn.
