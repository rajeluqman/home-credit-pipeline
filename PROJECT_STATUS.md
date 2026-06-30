# Home Credit Risk Pipeline — Project Status

> Resume-safe checkpoint. A fresh session reads "▶ RESUME HERE" first.
> Branch: `framework/governance-retrofit`. Retrofit source: `creative_intelligence_lab`
> (pipeline-retrofit effort, owner-approved 2026-06-28).

## ▶ RESUME HERE
**Where we are:** Governance retrofit (CLAUDE.md, 11-agent roster, hook, 3 contracts,
repo-map, 2 new ADRs, Confluence sync, logs, learning layer, simulation lab, INTERVIEW_GUIDE,
CI) built on `framework/governance-retrofit`. NOT pushed, NOT a PR yet — owner reviews first.
**Stack preserved as-is**: Glue PySpark (Silver) + dbt/Snowflake (Gold) + Airflow + Slack —
verified by reading the actual repo, not assumed from the master spec.
**Next action:** owner review → push branch → open PR → then port the pattern (not a literal
copy — stacks differ) to olist-ecommerce-pipeline.
**Do NOT:** push or open the PR without owner sign-off; swap any tool in the stack.

### ▶ Active thread — Phase-1 local-dev execution (2026-06-30)
Owner greenlit a **3-phase rollout** on REAL Kaggle data (spec:
`docs/ADDENDUM-A_local-dev-smart-sampling.md`, Proposed — pending @scope-guardian +
@data-architect sign-off):
1. **Phase 1 — local dev:** Codespace compute (Glue Docker, sample-only) + S3/Snowflake DEV
   storage, **no Airflow**. Engine = **Glue Docker primary** (runs `glue/*.py` unchanged →
   boundary contract literal-true; jobs are `awsglue.*`-coupled so plain PySpark is not a
   drop-in), Polars harness = documented fallback.
2. **Phase 2 — cloud:** promote same logic to real AWS Glue, full 58.4M.
3. **Phase 3 — orchestration:** wire the 3 Airflow DAGs, then migrate to main Airflow.
- **Flow B (owner decision 2026-06-30):** raw lands in the **S3 dev bucket** (durable SoT, never
  persisted in Codespace); `scripts/smart_sample.py` **streams** it from S3 (chunked). AWS egress
  accepted (credit covers it). Sampler reads/writes local **or** `s3://`.
- **Built this turn:** `scripts/smart_sample.py` (stratified + FK closure, S3-capable, manifest;
  smoke-tested local OK); `bronze/download_dataset.py --env dev` now uploads raw to S3 landing +
  deletes local (`--keep-local` to retain); `s3fs` added to `requirements.txt`. **s3fs auth to
  `home-credit-risk-dev-1` verified** (bucket exists, empty). All 4 gates green, ruff clean.
- **Synthetic data DELETED** (`data/*.csv`, `data/sample/`, `data/bronze/`) — real Kaggle only.
- **2026-06-30 — download + S3 landing + sample DONE.** Step 0 recheck before execution found one
  new gap not previously flagged: installed `boto3==1.43.37` required `botocore>=1.43.37` but the
  environment's `botocore` was pinned at `1.43.0` (held there by `aiobotocore`/`s3fs`, already
  proven working) — `ImportError` on `boto3.docs.utils`. Fixed by reinstalling `boto3==1.43.0`
  (`--no-deps`, matching the working `botocore` exactly) rather than upgrading `botocore` and
  risking the proven s3fs path; verified with a live `list_objects_v2` call before retrying.
  `requirements.txt` still pins `boto3==1.34.0` — stale vs. the working `1.43.0`, flagged for
  @data-platform-engineer, not changed here (out of this handover's scope).
  Kaggle auth confirmed live (`kaggle.api.competitions_list()`, `userHasEntered: true` for
  home-credit-default-risk — rules already accepted); auth flows through `~/.kaggle/kaggle.json`
  (auto-authenticated on `import kaggle`), not the `KAGGLE_API_TOKEN` env var that
  `validate_kaggle_credentials()` checks (that check is a no-op gate, not the real auth path).
  Disk: 18 GB free, sufficient. `bronze/download_dataset.py` confirmed still genuine Flow-B (not
  reverted by `setup.sh` — that heredoc is stale/divergent but hasn't been re-run).
  **Row counts verified** (`wc -l` on the downloaded CSVs before Flow-B delete) — all 7 match
  README.md "Source Tables" exactly: application_train 307,511 · bureau 1,716,428 · bureau_balance
  27,299,925 · previous_application 1,670,214 · installments_payments 13,605,401 · POS_CASH_balance
  10,001,358 · credit_card_balance 3,840,312. Raw landed in
  `s3://home-credit-risk-dev-1/landing/`, local copies deleted (Flow B end-state confirmed via
  `ls data/`).
  **Smart sample produced** (`data/sample/`, gitignored): 4,612/307,511 applicants (frac=0.015,
  seed=42), default_rate_sample 0.080659 vs default_rate_full 0.080729 (both ≈0.08, target met).
  Per-table rows: application_train 4,612 · bureau 21,799 · bureau_balance 211,766 ·
  previous_application 21,393 · installments_payments 172,406 · POS_CASH_balance 127,601 ·
  credit_card_balance 46,923. No dangling-FK warnings — the sampler closes every child table on
  the sampled parent ID set by construction (`scripts/smart_sample.py`), so there is no separate
  validation step to fail. Manifest: `data/sample/_manifest.json`.
  **4 gates re-run, all green:** `tests/identity_contract.py` OK · `tests/boundary_contract.py` OK
  · `tests/doc_reference_contract.py` OK (12 docs) · `scripts/gen_repo_map.py --check` OK (95 files).
- **Next:** addendum §9 open gaps remain (Bronze ingest still reads the naive 1000-row sample, not
  `data/sample/`; `setup.sh` heredoc still stale/divergent for `download_dataset.py`; Glue Docker
  unexercised; Snowflake/Databricks conn unverified) — out of scope for this download+sample
  handover, carried forward for the next phase.
- **2026-06-30 — fresh-session Step 0/Step 1 recheck (no redo needed).** A new Sonnet session was
  pointed at this same download→S3→sample task again; per CLAUDE.md read-before-touch it did not
  trust this file's claims and independently re-verified live: (a) Kaggle auth — `kaggle.api`
  resolves authenticated user `mamang10`; (b) disk — 18 GB free, unchanged; (c)
  `bronze/download_dataset.py:198-222` still has Flow-B intact (`--keep-local`, `upload_all_to_s3`,
  post-upload delete); `setup.sh:577`'s heredoc is still stale/divergent but has not been re-run, so
  no actual revert occurred. Live `s3.list_objects_v2` on `s3://home-credit-risk-dev-1/landing/`
  confirmed all 7 raw CSVs present; `data/sample/` + `_manifest.json` confirmed present and matching
  the figures above. All 4 gates re-run, all green. **Conclusion: Step 1 work was already done and
  is intact — re-download/re-upload was skipped as redundant** (owner confirmed via prompt).

### ▶ Active thread — Bronze→Silver Gate-1 proof on the sample (2026-06-30)
**Step 0 recheck found a NEW gap beyond addendum §9**, not previously documented: all 5 Glue
Silver jobs (`glue/glue_silver_*.py`) are hardcoded with **no local/dev branch** —
`spark.read.format("delta").load(f"s3://{bucket}/bronze/{table}/ingestion_date={date}/")` — while
Bronze dev-mode (`ingest_bronze.py::ingest_dev`) writes plain local Parquet, no `_delta_log`. A
literal "run unchanged Glue jobs over the Bronze sample output" was not executable without either
violating this file's own "no S3-upload of pipeline outputs in Phase 1" rule, or editing governed
`glue/` files. **Stopped and asked the owner**; owner chose a **one-time S3-upload override** for
this proof run (approved 2026-06-30) — supersedes the "Do NOT" line below for this run only.
- **Bronze repoint (addendum §9 gap #1, fixed):** `bronze/ingest_bronze.py:60-63` `ingest_dev()`
  now reads `data/sample/{filename}` for all 7 tables (was naive `application_train_dev_1000rows.csv`
  + ad-hoc `data/{filename}`). `tests/unit/test_bronze_ingest.py` fixtures updated to match — 22/22
  unit tests pass, ruff clean.
- **Two pre-existing bugs found and fixed in `gx/great_expectations.yml` (unrelated to the repoint
  — both suites had apparently never run successfully before this session):** (1) the
  `local_pandas` datasource only declared `default_inferred_data_connector_name`, but both
  `gx/run_bronze_suite.py` and `gx/run_silver_suite.py` request `default_runtime_data_connector_name`
  via `RuntimeBatchRequest` — added the missing `RuntimeDataConnector` block. (2) the 3 stores'
  `base_directory` values were written as `gx/expectations/`, `gx/validations/`,
  `gx/data_docs/local_site/` but `context_root_dir="gx"` is already passed in code, so GX resolved
  them relative to that and doubled the path to `gx/gx/...` (confirmed by `.gitignore` already
  expecting `gx/validations/` etc. un-nested) — stripped the redundant `gx/` prefix from all three;
  re-ran both suites after the fix, same PASS results, no more `gx/gx/` nesting.
- **Bronze run-evidence (env=dev, ingestion_date=2026-06-30, local + mirrored to S3 Delta):**
  application_train 4,612 · bureau 21,799 · bureau_balance 211,766 · previous_application 21,393 ·
  installments_payments 172,406 · POS_CASH_balance 127,601 · credit_card_balance 46,923 — 0
  quarantine rows across all 7 (PK never null on the sample). **GX bronze_suite (WARN): 7/7 PASS.**
- **Bronze→S3 Delta bridge (one-time, owner-approved):** new `bronze/promote_sample_to_s3.py` —
  explicitly scoped as a Phase-1-only proof utility, not part of the DAG chain; converts local
  Bronze Parquet → local Delta → uploads file-for-file to
  `s3://home-credit-risk-dev-1/bronze/{table}/ingestion_date=2026-06-30/`. Zero changes to
  `glue/*.py` — `tests/boundary_contract.py` still passes unchanged.
- **Glue Docker run (addendum §3, run-once → terminate):** pulled `amazon/aws-glue-libs:glue_libs_4.0.0_image_01`
  (9.4 GB; disk dropped from 18 GB → 8.7 GB free, within §4's ~9 GB headroom estimate). Found the
  base image ships the Delta Lake **JVM connector jars** (`delta-2.1.0/`) but not the Python `delta`
  package, and classpath wiring only activates via a `DATALAKE_FORMATS=delta` env var sourced through
  `.bashrc` (a login shell) — undocumented in the addendum, resolved via docker invocation flags only
  (`-e DATALAKE_FORMATS=delta`, login-shell `pip install --user delta-spark==2.1.0`, plus
  `--conf spark.sql.extensions=...DeltaSparkSessionExtension` / `--conf spark.sql.catalog.spark_catalog=...DeltaCatalog`
  on `spark-submit`) — **`glue/*.py` source files were not modified at all.** All 5 jobs
  (`glue_silver_application`, `glue_silver_bureau`, `glue_silver_balance_tables`,
  `glue_silver_installments`, `glue_silver_previous_application`) ran to completion, exit 0,
  committed Delta tables to `s3://home-credit-risk-dev-1/silver/`.
- **Silver run-evidence (7 tables produced by the 5 jobs):** silver_application 4,612 ·
  silver_bureau 21,799 · silver_bureau_balance 5,003 (post `MONTHS_BALANCE=0` filter, down from
  211,766 bronze rows) · silver_pos_cash 127,601 · silver_credit_card 46,923 · silver_installments
  162,862 (post dedup on `SK_ID_PREV`+`NUM_INSTALMENT_NUMBER`, down from 172,406) ·
  silver_previous_application 21,393. PII masking confirmed present on `silver_application`
  (`DAYS_BIRTH_MASKED`/`DAYS_EMPLOYED_MASKED` populated, raw `DAYS_BIRTH`/`DAYS_EMPLOYED` dropped
  from the Delta schema). Bridged back S3 Delta → local Parquet via the same
  `promote_sample_to_s3.py` script (`silver-down` direction) so `gx/run_silver_suite.py` ran
  **completely unmodified. GX silver_suite (FAIL gate): ALL PASS** (silver_application 3/3
  expectations incl. PII-mask check; silver_bureau + silver_bureau_balance `SK_ID_BUREAU`
  uniqueness).
- **4 gates re-run, all green:** `tests/identity_contract.py` OK · `tests/boundary_contract.py` OK ·
  `tests/doc_reference_contract.py` OK (12 docs) · `scripts/gen_repo_map.py --check` OK (107 files,
  regenerated after adding `bronze/promote_sample_to_s3.py` + the now-correctly-pathed
  `gx/expectations/*.json` suite files). `python -m pytest tests/unit/` 22/22 pass, ruff clean.
- **S3 state created by this override (not cleaned up):** `s3://home-credit-risk-dev-1/bronze/*/ingestion_date=2026-06-30/`
  and `s3://home-credit-risk-dev-1/silver/*/ingestion_date=2026-06-30/` — small Delta tables (sample
  scale, tens of MB total), left in place as the run-evidence artifact; flagged for
  @finops-agent awareness, not deleted without explicit instruction.
- **Backlog note (owner flagged mid-session, 2026-06-30):** synthetic data needs to eventually be
  purged from every layer it still touches (e.g. `bronze/generate_dev_data.py`'s fallback code path)
  — this will also require doc updates (`docs/ARCHITECTURE.md`, `ADDENDUM-A`, README "Source Tables"
  framing) once done. Not actioned in this increment — carried forward.
- **Gate 1 status:** Bronze→Silver proven on the sample with real run-evidence (this entry). Gate 1
  itself still needs Gold (dbt/Snowflake) to run end-to-end (separate, unverified — addendum §9) and
  explicit **@data-architect + @scope-guardian sign-off** before Phase 2 can start.
**Do NOT (Phase 1):** run AWS Glue *in the cloud* (Glue Docker — local Glue runtime — is the
sanctioned Phase-1 engine, see above); stand up Airflow; feed full source tables to the local Glue
container (sample-only — 27M `bureau_balance` would OOM). S3-upload of **raw** in dev IS allowed
(Flow B); S3-upload of pipeline *outputs* is normally Phase-2-only — **this session's
Bronze/Silver writes to S3 are a one-time, owner-approved exception for the Gate-1 proof
(2026-06-30), not a standing policy change.**

### ▶ Sonnet handover prompt (copy-paste into a fresh Sonnet session)
```
You are continuing the Home Credit pipeline on branch framework/governance-retrofit. This repo is
GOVERNED — obey CLAUDE.md's STOP-GATE + ANTI-SHORTCUT protocol: read-before-touch (read every file
THIS session, never assert from memory), enumerate don't sample, reconcile-before-done with
file:line evidence.

Phase-1 data acquisition (download → S3 landing → smart sample) AND Bronze→Silver execution on the
sample are DONE — see PROJECT_STATUS.md "▶ Active thread" 2026-06-30 entries for full evidence:
data acquisition (7/7 row counts verified, data/sample/ populated with 4,612 applicants, manifest
default_rate_sample 0.0807 ≈ full 0.0807) and the "Bronze→Silver Gate-1 proof" entry (Bronze 7/7 GX
PASS, all 5 Glue Silver jobs ran unchanged via Docker against real S3, Silver GX ALL PASS, 4 gates
green). Do not redo either.

Your task is the next increment toward Gate 1 (docs/ADDENDUM-A_local-dev-smart-sampling.md §5):
exercise the Gold layer (dbt models against Snowflake DEV) on the Silver output from this session,
so Gate 1's "Bronze→Silver→Gold runs end-to-end on the sample" checklist item is fully met. Read
the full addendum first (§5 Gate 1 checklist, §9 open gaps — Snowflake/Databricks connectivity is
flagged as unverified) plus PROJECT_STATUS.md "▶ Active thread" (both 2026-06-30 entries) before
touching anything — this repo is GOVERNED, obey CLAUDE.md's STOP-GATE + ANTI-SHORTCUT protocol
(read-before-touch, enumerate don't sample, reconcile-before-done with file:line evidence).

STEP 0 — RECHECK FOR MISSING GAPS BEFORE PROCEEDING (do this first, do not skip):
- Verify Snowflake DEV connectivity actually works (`.env.dev` SNOWFLAKE_* creds) — this was never
  proven in any prior session; don't assume it works.
- Check whether `dbt_home_credit/` models expect Silver input from S3 Delta (the locked
  architecture-of-record path) or whether a bridge is needed from this session's S3 Silver output
  (`s3://home-credit-risk-dev-1/silver/*/ingestion_date=2026-06-30/`) — read the actual dbt source
  configs, don't assume.
- Note the Bronze/Silver S3 writes from the prior session were an explicit one-time owner-approved
  override (not standing policy) — if Gold needs more S3 writes, that may need its own check-in
  rather than being assumed pre-approved.
- Report any NEW gap and STOP for owner confirmation if it conflicts with the plan.

STEP 1 — EXECUTE (only after Step 0 is clean):
1. Wire Silver (S3 Delta, written this session) into dbt's source layer.
2. Run the dbt models (staging → intermediate → mart) against Snowflake DEV.
3. Validate the Kimball star grain holds on the sample (SCD2 `dim_applicant`, fact grains) —
   `python tests/identity_contract.py` must still pass.
4. Capture real run-evidence (Gold table row counts, dbt test pass/fail) for Gate 1.

SCOPE — Gold (dbt/Snowflake) on the sample only. Do NOT: stand up Airflow, touch Databricks, or
commit any data. When done, update PROJECT_STATUS.md "▶ Active thread" with the run evidence, and
re-run the four gates. Gate 1 still needs explicit @data-architect + @scope-guardian sign-off after
this — getting Gold to run is necessary but not sufficient for the gate to be marked closed.
```

## Build checklist (with evidence)
| Item | Status | Evidence |
|---|---|---|
| CLAUDE.md | ✅ | `CLAUDE.md` — real Glue/Snowflake stack table, governed-file map |
| .claude/agents/ ×11 | ✅ | `.claude/agents/*.md` — 11 files (8 base + business-analyst/data-platform-engineer/documentation-sherpa replacing CIL's 8, +finops+infra-reality+cikgu) |
| .claude/hooks/governance_guard.py | ✅ | retargeted to `glue/`, `dbt_home_credit/models/mart/`, `dbt_home_credit/snapshots/`, `airflow/dags/` |
| tests/doc_reference_contract.py | ✅ | `python tests/doc_reference_contract.py` → OK, 11 docs |
| tests/boundary_contract.py | ✅ | `python tests/boundary_contract.py` → OK (after allowing pyspark in `bronze/` too — see "Doc gap found" below) |
| tests/identity_contract.py | ✅ | `python tests/identity_contract.py` → OK (SK_ID_CURR + SCD2 check) |
| scripts/gen_repo_map.py + REPO_MAP.md | ✅ | `python scripts/gen_repo_map.py --check` → OK, 61 files |
| ADR-002 PII-mask-order | ✅ | `docs/ADR/ADR-002-pii-mask-order.md` |
| ADR-003 Kimball-over-OBT sizing | ✅ | `docs/ADR/ADR-003-kimball-over-obt-sizing.md` |
| Confluence sync | ✅ | `scripts/sync_docs_to_confluence.py` adapted (PUBLISH_SET = real `docs/*.md`); `markdown`+`requests` added to `requirements.txt` |
| Logs (PROJECT_STATUS/COST_LOG/DECISION_LOG/INFRA_LIMITS_LOG) | ✅ | this file + the 3 below |
| learning/CURRICULUM.md + LEARNING_LOG.md | ⬜ | next |
| simulation/ | ⬜ | next |
| INTERVIEW_GUIDE.md | ⬜ | next |
| .github/workflows/ci.yml | ⬜ | next |
| push branch + PR | ⬜ | blocked on owner review (explicit instruction) |

## Doc gap found during retrofit (real finding, not assumed)
`docs/ARCHITECTURE.md` states "Silver transforms = AWS Glue (Spark) SAHAJA" — but
`bronze/ingest_bronze.py:99-100` imports `pyspark.sql` directly (via `delta-spark`, for
Delta Lake writes to S3 in `ingest_cloud()`). Spark is NOT actually Glue-exclusive; Bronze
cloud-mode ingestion also needs a SparkSession. `tests/boundary_contract.py` was written to
match this REALITY (allows pyspark in both `glue/` and `bronze/`), not the doc's stricter
claim. Flagged in `INTERVIEW_GUIDE.md` for an `docs/ARCHITECTURE.md` correction — not yet
fixed (owner decision: correct the doc, or move Bronze off delta-spark).

**2026-06-29 (owner audit ahead of a Microsoft Fabric migration):** `airflow/dags/
pipeline_dag.py` (dag_id `home_credit_risk_pipeline`) was an orphaned scaffold — generated by
`setup.sh`'s Phase-0 bootstrap, superseded by the real, separately-built
`bronze_ingestion_dag.py` / `silver_transforms_dag.py` / `gold_dbt_dag.py` (per README.md
"Project Structure"), but never deleted. It imported `bronze.bronze_pipeline` and
`silver.trigger_glue_job` — **neither module exists anywhere in this repo** (confirmed via
`find . -iname "*bronze_pipeline*" -o -iname "*trigger_glue*"` → zero hits); the task would
fail at runtime if Airflow ever executed it. **Resolved: removed** the committed file +
the `setup.sh` heredoc that generated it (owner approved deletion 2026-06-29 after the file's
brokenness was confirmed and presented). `architecture/REPO_MAP.md` regenerated to drop it.

## Resume↔repo reconciliation (preliminary — full table in INTERVIEW_GUIDE.md once written)
- **"Lambda, Step Functions"**: NOT found anywhere in the repo (`grep -rni "lambda\|step
  function"` across all `.py`/`.md` files returns zero infra hits — only Python `lambda`
  expressions in `silver/transforms.py`, which are language keywords, not AWS Lambda). Repo
  uses Glue + Airflow only. **Unsupported as written — needs resume correction or repo
  backfill.** (Note: `airflow/dags/pipeline_dag.py` previously also matched on this same
  `lambda`-keyword false positive — that file was removed 2026-06-29 as an orphaned, broken
  scaffold DAG; see "Doc gap found" below.)
- **"58M rows"**: supportable. Sum of the 7 source CSV row counts in README.md =
  307,511 + 1,716,428 + 27,299,925 + 1,670,214 + 13,605,401 + 10,001,358 + 3,840,312 =
  **58,441,149** rows. **Confirmed.**

## Decision log (this effort)
- 2026-06-28: Cloned to `framework/governance-retrofit`, read-before-touch on every real file
  before writing governance artifacts. boundary_contract.py written against observed reality
  (pyspark in bronze/ too) rather than the doc's stricter wording — doc gap named, not silenced.
