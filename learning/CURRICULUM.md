# Curriculum — Home Credit Risk Pipeline (rebuild-from-scratch)

> @cikgu's module path. Goal: owner can rebuild every layer of this pipeline from scratch on a
> `drill/*` branch and defend every resume claim in an interview. Mental-model → ETL use-case
> → production bug → debug → syntax LAST (owner's proven teaching order).

## M0 — Orientation
- What: read `docs/BRD.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md` cold (no code yet).
- Why-before-how: why Kimball over OBT for THIS dataset shape (27M-row bureau_balance), not
  "what is a star schema" in the abstract.
- DIY: explain the medallion flow (Bronze→Silver→Gold) back, in your own words, citing the ADR.

## M1 — Bronze ingestion
- Concept: idempotent ingestion, PK-null quarantine, `ingestion_ts`/`ingestion_date` metadata.
- Artifact (read only after attempting the ticket): `bronze/ingest_bronze.py`.
- Production bug angle: what happens if a Kaggle CSV is re-downloaded mid-run and a row's PK
  changes type (str vs int)? Trace the quarantine path.
- DIY ticket: `learning/diy/TICKET_bronze_ingest.md`.

## M2 — Silver: PII masking order (ADR-002)
- Concept: WHY sentinel-null must happen before hashing (see ADR-002's "why this order"
  section) — this is the highest-value module, it's also the PII-mask-order ADR you just helped
  write.
- Artifact: `glue/glue_silver_application.py` + `silver/transforms.py` (the pandas mirror).
- DIY ticket: reproduce `silver/transforms.py`'s masking function without looking at it first.

## M3 — Silver: Glue job mechanics
- Concept: G.1X×2 worker sizing, MERGE upsert idempotency, why standalone PySpark elsewhere is
  forbidden (`tests/boundary_contract.py` ST1).
- Artifact: `glue/glue_silver_bureau.py` (bureau + bureau_balance MONTHS_BALANCE=0 filter).
- Production bug angle: what if a re-run of this job double-counts because the MERGE key is wrong?

## M4 — Gold: dbt staging → intermediate → mart
- Concept: 3-layer dbt structure, `generate_surrogate_key` macro, FK tests
  (`assert_fk_loan_application_applicant.sql`).
- Artifact: `dbt_home_credit/models/{staging,intermediate,mart}/`.
- DIY ticket: build `fact_installment_payment.sql` from the spec without opening the real file.

## M5 — SCD Type 2 (the resume-proof centerpiece)
- Concept: `dbt snapshot`, `strategy: check`, `dbt_valid_from`/`dbt_valid_to` → `start_date`/
  `end_date`/`is_current`. Run `tests/identity_contract.py` to see the static gate that
  protects this.
- Artifact: `dbt_home_credit/snapshots/snap_applicant.sql` + `dbt_home_credit/models/mart/dim_applicant.sql`.
- Interview drill: "why SCD2 here and not SCD1 for every dim?" — answer from the artifact, not memory.

## M6 — Orchestration + alerting
- Concept: 3 chained Airflow DAGs, Slack on_failure wiring (`SlackWebhookOperator` +
  curl `BashOperator` fallback in `gold_dbt_dag.py`).
- Artifact: `airflow/dags/*.py`.

## M7 — Quality gates
- Concept: WARN-vs-FAIL GX gate design (`gx/run_bronze_suite.py` WARN, `gx/run_silver_suite.py` FAIL).
- Artifact: `gx/run_silver_suite.py`.

## M8 — Defend the resume
- Read `INTERVIEW_GUIDE.md`'s Resume Claim ↔ Repo Evidence table.
- Drill the 2 open reconciliation items (Lambda/Step Functions — unsupported; 58M rows —
  confirmed) until you can explain both without notes.

## Drill mechanics
All M1-M7 DIY work happens on `drill/<module>` branches, never `main`. `learning/diy/`
tickets are WHAT not HOW. Score tracked in `LEARNING_LOG.md` (start 100, hint = -5).
