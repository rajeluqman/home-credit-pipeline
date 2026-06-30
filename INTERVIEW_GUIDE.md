# Interview Guide — Home Credit Risk Pipeline

> Owned jointly by @business-analyst (evidence) and @documentation-sherpa (structure).
> Every resume bullet traces to `file:line` evidence below, or is flagged unsupported.
> "(unverified)" means checked-but-not-confirmed this turn (e.g. no local pytest/AWS available);
> never silently upgraded to "confirmed" without re-running the check.

## Resume Claim ↔ Repo Evidence

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1 | "Engineered a scalable ingestion pipeline integrating 300k+ credit records from 7 disparate source tables with full schema alignment" | ✅ Confirmed | `docs/BRD.md:24-27` (the repo's own stated resume entry) + README.md "Source Tables" table — 7 CSVs, application_train.csv = 307,511 rows |
| 2 | "automated data quality gating via Great Expectations" | ✅ Confirmed | `gx/run_bronze_suite.py`, `gx/run_silver_suite.py` — both real files, real GX `RuntimeBatchRequest` usage |
| 3 | "PII masking (SHA-256)" | ✅ Confirmed | `silver/transforms.py` `_sha256()` (`hashlib.sha256`), `glue/glue_silver_application.py` — mask order made binding in `docs/ADR/ADR-002-pii-mask-order.md` |
| 4 | "SCD Type 2 historical tracking for compliance" | ✅ Confirmed | `dbt_home_credit/snapshots/snap_applicant.sql` (`strategy: check`), `dbt_home_credit/models/mart/dim_applicant.sql`, gated by `tests/identity_contract.py` |
| 5 | "58M rows" (across the 7 source tables) | ✅ Confirmed | README.md "Source Tables" row counts sum to 58,441,149 (307,511 + 1,716,428 + 27,299,925 + 1,670,214 + 13,605,401 + 10,001,358 + 3,840,312) |
| 6 | "Lambda, Step Functions" | ❌ Unsupported | `grep -rni "lambda\|step function"` across the repo (excluding Python `lambda` expressions, which are language keywords, not AWS Lambda) finds **zero** AWS Lambda or Step Functions usage. Orchestration is Apache Airflow (`airflow/dags/*.py`); Silver compute is AWS Glue (`glue/*.py`). **Action needed: either correct the resume wording (drop Lambda/Step Functions, say "Airflow + Glue") or, if Lambda/Step Functions exist in a part of the project not in this repo, point to that evidence — currently none found here.** |
| 7 | "22/22 pytest" (README.md "Phase Completion" Phase 4a) | ✅ Confirmed | `tests/unit/test_bronze_ingest.py` = 5 `def test_` functions, `tests/unit/test_silver_transforms.py` = 17 `def test_` functions → 5+17 = 22, matching exactly. **(unverified that all 22 currently PASS — no pytest installed in this build environment; owner should run `pytest tests/unit/ -v` locally to confirm green, not just count-match.)** |
| 8 | "Kimball Star Schema" / SCD2 as the modelling paradigm | ✅ Confirmed | `docs/ADR/ADR-001-kimball-star-schema.md`, sizing math made explicit in `docs/ADR/ADR-003-kimball-over-obt-sizing.md` |
| 9 | "Slack alerting" | ✅ Confirmed | `airflow/dags/gold_dbt_dag.py:13,29-36,74-86` — `SlackWebhookOperator` + curl `BashOperator` fallback |

## Doc gap surfaced during retrofit (separate from resume reconciliation)
`docs/ARCHITECTURE.md` claims "Silver transforms = AWS Glue (Spark) SAHAJA" — but
`bronze/ingest_bronze.py:99-100` also imports `pyspark.sql` (via `delta-spark`, for Delta Lake
writes in `ingest_cloud()`). Spark is not Glue-exclusive in this repo as currently built. This
doesn't affect the resume claims above, but the owner should decide: correct
`docs/ARCHITECTURE.md`'s wording, or refactor Bronze off delta-spark to make the doc true.
Logged in `PROJECT_STATUS.md` "Doc gap found."

**(found + resolved 2026-06-29, owner audit ahead of a Microsoft Fabric migration):**
`airflow/dags/pipeline_dag.py` was a broken, orphaned scaffold DAG (imported 2 modules that
don't exist in this repo — see `PROJECT_STATUS.md`). If asked "walk me through your Airflow
setup," answer from the 3 REAL DAGs only (`bronze_ingestion_dag.py`, `silver_transforms_dag.py`,
`gold_dbt_dag.py`) — the orphaned file was removed, not a 4th DAG that ever ran.

## Interview Q&A drills (answer from the artifact, not memory)
1. **"Why Kimball over OBT?"** → cite `docs/ADR/ADR-001` + the sizing math in `ADR-003`
   (G.1X×2 ≈ 32GB executor ceiling vs 27M-row bureau_balance fan-out risk).
2. **"Why mask DAYS_EMPLOYED in that specific order?"** → cite `docs/ADR/ADR-002` (sentinel-null
   before hash — hashing 365243 first would leak a categorical signal).
3. **"Walk me through your SCD2 implementation."** → `dbt snapshot` strategy `check`, 4 tracked
   columns, `dbt_valid_to IS NULL` → `is_current`; gated by `assert_scd2_one_current_per_applicant.sql`
   AND the static `tests/identity_contract.py`.
4. **"What's your free-tier risk and how did you size around it?"** → `INFRA_LIMITS_LOG.md` +
   ADR-003.
