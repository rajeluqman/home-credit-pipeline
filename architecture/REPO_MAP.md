# REPO_MAP — generated navigation index

> **GENERATED — do not hand-edit.** `python scripts/gen_repo_map.py` rebuilds it from
> ground truth; CI runs `--check` and fails if this file is stale. Purpose is extracted
> from each file's own docstring / first heading / leading comment; *Uses* and *Used by*
> are parsed (`ast` for Python, `ref()` for dbt), never authored.
>
> **This is a pointer, not a cache.** It tells you which file to open — then READ THAT
> FILE FRESH before you edit or assert about it (ANTI-SHORTCUT PROTOCOL, CLAUDE.md).

**107 files mapped.**

## Architecture Decision Records

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `docs/ADR/ADR-001-kimball-star-schema.md` | ADR-001: Data Modelling Paradigm — Kimball Star Schema | — | — |
| `docs/ADR/ADR-002-pii-mask-order.md` | ADR-002: PII Masking Order — Sentinel-Null Before SHA-256 | — | — |
| `docs/ADR/ADR-003-kimball-over-obt-sizing.md` | ADR-003: Kimball-over-OBT Sizing Math (free-tier Glue OOM risk) | — | — |

## Top-level docs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `CLAUDE.md` | Home Credit Risk Pipeline — AI Context | — | — |
| `COST_LOG.md` | Cost Log — Home Credit Risk Pipeline | — | — |
| `DECISION_LOG.md` | Decision Log — Home Credit Risk Pipeline | — | — |
| `INFRA_LIMITS_LOG.md` | Infra Limits Log — Home Credit Risk Pipeline | — | — |
| `INTERVIEW_GUIDE.md` | Interview Guide — Home Credit Risk Pipeline | — | — |
| `PROJECT_STATUS.md` | Home Credit Risk Pipeline — Project Status | — | — |
| `README.md` | home-credit-risk-pipeline | — | — |
| `confluence/00_START_HERE.md` | Start Here — Home Credit Risk Pipeline | — | — |
| `docs/ADDENDUM-A_local-dev-smart-sampling.md` | Addendum A — Local-Dev Execution & Smart Sampling (Phase 1) | — | — |
| `docs/ARCHITECTURE.md` | Architecture: Home Credit Risk Pipeline | — | — |
| `docs/BRD.md` | BRD: Home Credit Risk Pipeline | — | — |
| `docs/DATA_DICTIONARY.md` | Data Dictionary: Home Credit Risk Pipeline | — | — |
| `docs/DATA_MODEL.md` | Data Model: Home Credit Risk Pipeline | — | — |
| `docs/DQD.md` | DQD: Home Credit Risk Pipeline | — | — |
| `docs/DRD.md` | DRD: Home Credit Risk Pipeline | — | — |
| `docs/OPS_RUNBOOK.md` | OPS Runbook: Home Credit Risk Pipeline | — | — |
| `docs/PIPELINE_SPEC.md` | Pipeline SPEC: Home Credit Risk Pipeline | — | — |

## dbt — staging

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/models/staging/schema.yml` | — | — | — |
| `dbt_home_credit/models/staging/stg_application.sql` | Source: silver_application (Snowflake Silver schema) | — | dim_loan_type.sql, fact_loan_application.sql, int_applicant_attributes.sql |
| `dbt_home_credit/models/staging/stg_bureau.sql` | Source: silver_bureau | — | int_bureau_with_balance.sql |
| `dbt_home_credit/models/staging/stg_bureau_balance.sql` | Source: silver_bureau_balance (1 row per SK_ID_BUREAU — MONTHS_BALANCE=0) | — | int_bureau_with_balance.sql |
| `dbt_home_credit/models/staging/stg_installments.sql` | Source: silver_installments | — | int_installment_payments.sql |

## dbt — intermediate

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/models/intermediate/int_applicant_attributes.sql` | Select tracked SCD2 columns + PII masked columns from stg_application. | stg_application.sql | snap_applicant.sql |
| `dbt_home_credit/models/intermediate/int_bureau_with_balance.sql` | Join silver_bureau + silver_bureau_balance. | stg_bureau.sql, stg_bureau_balance.sql | fact_bureau_credit.sql |
| `dbt_home_credit/models/intermediate/int_installment_payments.sql` | Add derived column days_payment_diff. | stg_installments.sql | fact_installment_payment.sql |
| `dbt_home_credit/models/intermediate/schema.yml` | — | — | — |

## dbt — mart

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/models/mart/dim_applicant.sql` | SCD Type 2 dimension — aliases snap_applicant dbt columns to resume-aligned names. | snap_applicant.sql | assert_fk_bureau_credit_applicant.sql, assert_fk_loan_application_applicant.sql, assert_scd2_one_current_per_applicant.sql, fact_bureau_credit.sql, fact_loan_application.sql |
| `dbt_home_credit/models/mart/dim_credit_status.sql` | SCD Type 1 — static mapping for CREDIT_ACTIVE values from silver_bureau. | — | fact_bureau_credit.sql |
| `dbt_home_credit/models/mart/dim_loan_type.sql` | SCD Type 1 — static lookup from distinct contract types in silver_application. | stg_application.sql | fact_loan_application.sql |
| `dbt_home_credit/models/mart/fact_bureau_credit.sql` | Grain: 1 row = 1 bureau credit record (SK_ID_BUREAU). | dim_applicant.sql, dim_credit_status.sql, int_bureau_with_balance.sql | assert_fk_bureau_credit_applicant.sql |
| `dbt_home_credit/models/mart/fact_installment_payment.sql` | Grain: 1 row = 1 installment payment (SK_ID_PREV + NUM_INSTALMENT_NUMBER). | int_installment_payments.sql | — |
| `dbt_home_credit/models/mart/fact_loan_application.sql` | Grain: 1 row = 1 loan application (SK_ID_CURR). | dim_applicant.sql, dim_loan_type.sql, stg_application.sql | assert_fk_loan_application_applicant.sql |
| `dbt_home_credit/models/mart/schema.yml` | — | — | — |

## dbt — snapshots

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/snapshots/snap_applicant.sql` | (no leading -- comment) | int_applicant_attributes.sql | dim_applicant.sql |

## dbt — tests

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/tests/assert_fk_bureau_credit_applicant.sql` | FK integrity: every fact_bureau_credit.applicant_sk must resolve in dim_applicant. | dim_applicant.sql, fact_bureau_credit.sql | — |
| `dbt_home_credit/tests/assert_fk_loan_application_applicant.sql` | FK integrity: every fact_loan_application.applicant_sk must resolve in dim_applicant. | dim_applicant.sql, fact_loan_application.sql | — |
| `dbt_home_credit/tests/assert_scd2_one_current_per_applicant.sql` | SCD2 invariant: exactly 1 is_current=TRUE per applicant_id. | dim_applicant.sql | — |

## dbt — macros

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/macros/generate_surrogate_key.sql` | (no leading -- comment) | — | — |
| `dbt_home_credit/macros/test_not_in.sql` | (no leading -- comment) | — | — |

## dbt — other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_home_credit/.user.yml` | — | — | — |
| `dbt_home_credit/dbt_project.yml` | — | — | — |
| `dbt_home_credit/models/sources.yml` | — | — | — |

## AWS Glue (Silver, PySpark)

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `glue/glue_silver_application.py` | AWS Glue 4.0 — Silver Application Transform | — | — |
| `glue/glue_silver_balance_tables.py` | AWS Glue 4.0 — Silver POS Cash + Credit Card Balance Transform | — | — |
| `glue/glue_silver_bureau.py` | AWS Glue 4.0 — Silver Bureau + Bureau Balance Transform | — | — |
| `glue/glue_silver_installments.py` | AWS Glue 4.0 — Silver Installments Payments Transform | — | — |
| `glue/glue_silver_previous_application.py` | AWS Glue 4.0 — Silver Previous Application Transform | — | — |

## Bronze ingestion

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `bronze/download_dataset.py` | WHAT : Download Home Credit dataset dari Kaggle Competition API | — | — |
| `bronze/generate_dev_data.py` | Generate synthetic dev data for Phase 4a local testing. | — | — |
| `bronze/ingest_bronze.py` | Bronze ingestion — parameterised by --table and --env. | — | — |
| `bronze/promote_sample_to_s3.py` | Phase-1 Gate-1 bridge — owner-approved one-time override (PROJECT_STATUS.md | — | — |

## Silver (local/pandas mirror)

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `silver/transforms.py` | Pandas-based Silver transforms — mirrors the PySpark logic in glue/. | — | — |

## Airflow DAGs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `airflow/dags/bronze_ingestion_dag.py` | bronze_ingestion_dag — ingest all 7 tables → Bronze Delta/S3, then GX, then trigger Silver. | — | — |
| `airflow/dags/gold_dbt_dag.py` | gold_dbt_dag — dbt run (staging → intermediate → snapshot → mart) → dbt test → Slack. | — | — |
| `airflow/dags/silver_transforms_dag.py` | silver_transforms_dag — trigger 5 Glue jobs → GX silver suite → trigger Gold. | — | — |

## Great Expectations suites

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `gx/.gitignore` | — | — | — |
| `gx/expectations/.ge_store_backend_id` | — | — | — |
| `gx/expectations/bronze_POS_CASH_balance_suite.json` | — | — | — |
| `gx/expectations/bronze_application_train_suite.json` | — | — | — |
| `gx/expectations/bronze_bureau_balance_suite.json` | — | — | — |
| `gx/expectations/bronze_bureau_suite.json` | — | — | — |
| `gx/expectations/bronze_credit_card_balance_suite.json` | — | — | — |
| `gx/expectations/bronze_installments_payments_suite.json` | — | — | — |
| `gx/expectations/bronze_previous_application_suite.json` | — | — | — |
| `gx/expectations/silver_application_suite.json` | — | — | — |
| `gx/expectations/silver_bureau_balance_suite.json` | — | — | — |
| `gx/expectations/silver_bureau_suite.json` | — | — | — |
| `gx/great_expectations.yml` | — | — | — |
| `gx/plugins/custom_data_docs/styles/data_docs_custom_styles.css` | — | — | — |
| `gx/run_bronze_suite.py` | Run GX bronze_suite against Bronze parquet files (dev: local, cloud: S3). | — | — |
| `gx/run_silver_suite.py` | Run GX silver_suite — validates Silver layer data quality gates. | — | — |

## Tests / contracts

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `tests/boundary_contract.py` | Stack + scope boundary contract — deterministic gate over this repo's locked stack. | — | — |
| `tests/doc_reference_contract.py` | Doc-reference contract — deterministic gate against documentation drift. | — | — |
| `tests/identity_contract.py` | Identity contract — deterministic gate over the SCD2 applicant grain. | — | — |
| `tests/unit/test_bronze_ingest.py` | Unit tests for bronze/ingest_bronze.py — dev mode (local parquet, no AWS). | — | — |
| `tests/unit/test_silver_transforms.py` | Unit tests for silver/transforms.py — tests all transform functions with pandas. | — | — |

## Governance hooks

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.claude/hooks/governance_guard.py` | Governance hook — makes Claude check governed docs/ADRs BEFORE and AFTER touching governed | — | — |

## Cabinet agents

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.claude/agents/business-analyst.md` | name: business-analyst | — | — |
| `.claude/agents/cikgu.md` | name: cikgu | — | — |
| `.claude/agents/data-architect.md` | name: data-architect | — | — |
| `.claude/agents/data-platform-engineer.md` | name: data-platform-engineer | — | — |
| `.claude/agents/data-quality-steward.md` | name: data-quality-steward | — | — |
| `.claude/agents/documentation-sherpa.md` | name: documentation-sherpa | — | — |
| `.claude/agents/finops-agent.md` | name: finops-agent | — | — |
| `.claude/agents/infra-reality-agent.md` | name: infra-reality-agent | — | — |
| `.claude/agents/product-owner.md` | name: product-owner | — | — |
| `.claude/agents/scope-guardian.md` | name: scope-guardian | — | — |
| `.claude/agents/senior-data-engineer.md` | name: senior-data-engineer | — | — |

## Learning

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `learning/CURRICULUM.md` | Curriculum — Home Credit Risk Pipeline (rebuild-from-scratch) | — | — |
| `learning/LEARNING_LOG.md` | Learning Log — Home Credit Risk Pipeline | — | — |

## Simulation lab

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `simulation/ISOLATION_CONTRACT.md` | Isolation Contract — Home Credit Simulation Lab | — | — |
| `simulation/check_isolation.py` | Isolation guard for the Home Credit simulation lab (simulation/). | — | — |
| `simulation/faults/README.md` | Fault Catalog — Home Credit Simulation Lab | — | — |
| `simulation/faults/inject.py` | Inject a named, reversible fault into the SIM lab only (never touches real models). | — | — |
| `simulation/faults/reset.py` | Reset the SIM lab to clean baseline — re-seed + re-build sim only. Never hand-patched. | — | — |
| `simulation/sim_dbt/dbt_project.yml` | — | — | — |
| `simulation/specs/01_SIM_glue_oom_troubleshoot.md` | SIM Spec — Glue OOM Troubleshoot Drill | — | — |

## Config

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.mcp.json` | — | — | — |
| `gold/profiles.yml` | — | — | — |
| `setup.sh` | — | — | — |

## Other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `requirements.txt` | — | — | — |
| `scripts/gen_repo_map.py` | Repo-map generator — the NAVIGATION half of the ANTI-SHORTCUT PROTOCOL (see CLAUDE.md). | — | — |
| `scripts/smart_sample.py` | Smart sampler — stratified anchor + referential closure over the 7 Home Credit source CSVs. | — | — |
| `scripts/sync_docs_to_confluence.py` | Publish this repo's real docs/ set to Confluence as living documentation. | — | — |
