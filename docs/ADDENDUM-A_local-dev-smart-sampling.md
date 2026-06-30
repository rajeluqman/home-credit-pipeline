# Addendum A — Local-Dev Execution & Smart Sampling (Phase 1)

> **Status:** Proposed — pending owner + @scope-guardian + @data-architect sign-off
> **Date:** 2026-06-30
> **Owner:** Senior Data Engineer (build) · Scope Guardian (boundary) · Data Architect (identity)
> **Amends:** `docs/ARCHITECTURE.md` — **for the Phase-1 development stage ONLY**. The locked
> stack (S3 → AWS Glue Silver → dbt/Snowflake Gold → Airflow) is **unchanged** as the
> architecture of record. This addendum scopes a *temporary, dev-only* execution mode and the
> promotion gates back to that cloud stack. It does **not** swap any tool.

---

## 1. Why this addendum exists

The retrofit unlocked use of the **real Home Credit datasets**. Before paying for cloud compute
(AWS Glue) and running 58.4M rows, we want to prove the full Bronze→Silver→Gold logic **locally,
cheaply, on a representative slice**. That means a three-phase rollout:

| Phase | Compute | Storage | Orchestration | Goal |
|-------|---------|---------|---------------|------|
| **1 — Local dev** *(this addendum)* | **Codespace** (local Glue Docker, sample only) | **AWS S3** (dev bucket) + Snowflake DEV | Manual / Makefile — **no Airflow** | Prove smart-sample → Silver → Gold end-to-end, GX green |
| **2 — Cloud** | **AWS Glue** (real), full 58.4M | S3 + Snowflake STAGING/PROD | Manual trigger | Promote logic to cloud at full scale |
| **3 — Orchestration** | (as Phase 2) | (as Phase 2) | **Apache Airflow** (3 chained DAGs) → migrate to main Airflow | Automate the chain + Slack alerting |

Each arrow is a **promotion gate** (§5). We do not skip ahead: Phase 2 starts only after Gate 1
passes; Phase 3 only after Gate 2.

---

## 2. Smart sampling spec

**Phase 1 uses real Kaggle data only.** The synthetic dev CSVs were deleted (2026-06-30); the
synthetic-data generator script (formerly bronze/generate_dev_data.py) was removed entirely
(2026-06-30, owner decision — supersedes the earlier "keep as offline fallback" call) — synthetic
data cannot validate real value distributions, PII patterns, or referential edge cases, and the
generator wrote to the same filenames as real Kaggle downloads (data/application_train.csv etc.),
a live contamination risk if ever run by mistake. The sampler is `scripts/smart_sample.py` (built
2026-06-30).

**Flow B — raw is the durable S3 source-of-truth, never persisted in Codespace.** The Kaggle API
must write to a local filesystem (no direct Kaggle→S3 pipe), so raw transits Codespace **once**
during download, is uploaded to the **S3 dev landing zone** (`s3://<S3_BUCKET_DEV>/landing/`), and
the local copy is then deleted. `scripts/smart_sample.py` **streams** the raw from S3 (chunked) —
the 7 GB never persists on the ephemeral Codespace disk. S3↔Codespace egress is accepted
(AWS credit covers it; owner decision 2026-06-30). The small slice lands locally in `data/sample/`
for the Glue Docker run.

**Strategy: stratified anchor + full referential closure.**

1. **Anchor & stratify.** Select N applicants from the real `application_train.csv` (streamed
   from S3 landing) **stratified by `TARGET`**, preserving the real default rate (~8% positive) in
   the sample. Target size: **~1–2% of applicants (≈3,000–6,000 `SK_ID_CURR`)** — fits Codespace
   RAM (§4).
2. **Referential closure** — follow the foreign keys so no downstream join is left dangling:

   ```
   application_train  ──SK_ID_CURR──┬──→ bureau ──SK_ID_BUREAU──→ bureau_balance
                                     └──→ previous_application ──SK_ID_PREV──┬──→ installments_payments
                                                                             ├──→ POS_CASH_balance
                                                                             └──→ credit_card_balance
   ```

   Keep **every** child row whose key is in the chosen applicant set. The sample is therefore
   *self-consistent*: every fact row resolves to a sampled applicant, and SCD2 / identity checks
   hold on the slice exactly as they would on the full set.

3. **Output.** Seven sampled CSVs under *data/sample/* (gitignored — never committed; see
   CLAUDE.md "What NOT to commit"), same schema/filenames as source. A manifest records the seed,
   N, realised default rate, and per-table row counts for reproducibility.

**Why stratified, not random:** on a slice this small a simple random draw can drift the default
rate, which would silently bias every Gold KPI and DQ threshold. Stratifying on `TARGET` keeps
the slice honest. (Owner decision 2026-06-30.)

---

## 3. Local execution mode — `Glue Docker`, sample-only

Phase-1 Silver runs the **actual** Silver job code (under `glue/`) inside the official
`amazon/aws-glue-libs` container in Codespace — **not** a rewritten local-PySpark or
DuckDB variant. Rationale:

- **Boundary contract stays literally true.** `tests/boundary_contract.py` (ST1) forbids Spark
  *outside Glue*. The Glue Docker image **is** Glue — same runtime, same libraries — so running
  it locally does not violate the rule. No contract amendment, no scope-creep waiver needed.
- **One code path.** The same Silver job that runs in Codespace runs unchanged in AWS Glue at
  Phase 2. Promotion = point it at the full dataset + real cluster, not a rewrite.
- **$0.** No AWS Glue DPU spend during iteration.

Operational shape: **run-once → terminate.** Pull image, run the job over *data/sample/*,
`docker rm` the container. Not a long-lived service.

> **Note — `awsglue` coupling (verified 2026-06-30):** all five Silver jobs under `glue/`
> import `awsglue.context.GlueContext`, `awsglue.job.Job`, `awsglue.utils.getResolvedOptions`,
> and `awsglue.transforms`. Those libraries are **not** plain-pip-installable — they ship with
> the Glue runtime. So running the jobs *unchanged* **requires** Glue libs (the Docker image or
> the `aws-glue-libs` local install). A bare `pip install pyspark` would ImportError on
> `awsglue` — it is therefore **not** a lighter drop-in, and is rejected.

### 3a. Documented fallback — Polars/DuckDB harness (if JVM chokes Codespace)

The Glue JVM is heavy for a 2-vCPU / 4.8-GB-free / no-swap box. If, in practice, the container
OOMs or is unworkably slow even on the sample, the **sanctioned fallback** is a lightweight
**Polars (or DuckDB) dev-harness** that re-expresses the Silver transforms over *data/sample/*:

- **Contract-safe:** Polars/DuckDB are not Spark, so `tests/boundary_contract.py` (ST1) is not
  triggered — no amendment, no waiver.
- **Cost — divergence:** the Silver logic is then written twice (dev harness vs. prod `glue/`).
  To contain that, the fallback is admitted **only with a parity test** asserting the harness and
  the Glue job produce *identical* Silver output on the sample, so the two implementations cannot
  silently drift.
- **Prod is unaffected:** Phase 2 still promotes the *Glue* jobs to AWS; the harness never leaves
  Phase 1.

Primary path stays Glue Docker. This fallback is the documented exit, not the default.

---

## 4. Infra reality (Codespace ceiling — measured 2026-06-30)

| Resource | Available | Note |
|----------|-----------|------|
| vCPU | 2 | Spark runs; keep parallelism low |
| RAM | 7.8 GB total / ~4.8 GB free / **no swap** | Set Spark driver ≈ 2g; **sample-only** — the full 27M-row `bureau_balance` would OOM (consistent with ADR-003's free-tier sizing math) |
| Disk | ~18 GB free | Glue image ≈ 9 GB uncompressed → fits, ~9 GB headroom left |
| Docker | v29, image not yet pulled | — |

**Hard constraint (owned by @infra-reality):** Phase 1 **never** feeds full source tables to the
local container. The smart sample is the mechanism that makes local Spark viable here. Full-scale
runs belong to Phase 2 on AWS Glue, where ADR-003's 32 GB executor budget applies.

---

## 5. Sign-off gate protocol

No phase advances without its gate. A gate is a checklist with `file:line` evidence (per the
CLAUDE.md anti-shortcut protocol), signed by the named veto holder.

**Gate 1 — Phase 1 → Phase 2** *(local proven)* — **CLOSED 2026-06-30**, see
`PROJECT_STATUS.md` "▶ @scope-guardian Gate-1 sign-off" + "▶ @data-architect Gate-1 sign-off"
- [x] Smart sample passes `tests/identity_contract.py` (SK_ID_CURR + SCD2 one-current-per-applicant)
- [x] Sample passes `tests/boundary_contract.py` (clean) and `tests/doc_reference_contract.py`
  (9 pre-existing parser-limitation false positives, independently confirmed by both veto holders
  via spot-check — every referenced file genuinely exists on disk; not new drift, not a grain/
  scope issue — see `PROJECT_STATUS.md` sign-off entries for the file:line evidence)
- [x] Bronze→Silver→Gold runs end-to-end on the sample; GX bronze (WARN) + silver (FAIL) suites green
- [x] Real run-evidence captured (fact/dim row counts, DQ pass rates) in `PROJECT_STATUS.md`
- [x] **Sign-off:** @data-architect (grain/identity preserved on slice) **+** @scope-guardian (engine = Glue, no boundary breach) — both APPROVE, 2026-06-30

**Gate 2 — Phase 2 → Phase 3** *(cloud proven)*
- [ ] Same logic runs on full 58.4M via real AWS Glue → Snowflake STAGING/PROD
- [ ] Glue job stays within free-tier executor memory (no OOM on `bureau_balance`)
- [ ] **Sign-off:** @finops-agent (AWS free-tier + Snowflake credit) **+** @infra-reality-agent (OOM)

**Gate 3 — Phase 3 complete** *(orchestrated)*
- [ ] 3 chained Airflow DAGs (bronze→silver→gold) green; Slack alert fires on pass/fail
- [ ] Settings migrated to main Airflow instance
- [ ] **Sign-off:** @data-platform-engineer

---

## 6. What changes vs. what does NOT

**Does NOT change** (architecture of record intact):
- The locked stack and tool choices (`docs/ARCHITECTURE.md`).
- The Kimball star schema, grain, SCD2 strategy (ADR-001, `docs/DATA_MODEL.md`).
- The PII mask order (ADR-002), the boundary contract, the identity contract.
- The governance hook, the 11-agent cabinet, the three CI contracts.

**Does change** (Phase-1 only, reverts at Phase 2):
- Compute *location* for Silver: Codespace-local Glue container, not AWS-hosted Glue.
- Input *volume*: a stratified, FK-closed real-data sample, not the full 58.4M rows.
- Orchestration: none (manual) until Phase 3.

---

## 7. Artifacts — built vs. backlog

**Built (2026-06-30):**
- `scripts/smart_sample.py` — stratified + FK-closure sampler, reads local **or** `s3://` (Flow B),
  chunked reads, writes a `_manifest.json`. Smoke-tested (default rate + FK closure preserved).
- `bronze/download_dataset.py` `--env dev` — now lands raw in the S3 dev bucket and deletes the
  local copy (`--keep-local` to retain).
- `s3fs` added to `requirements.txt` (pandas `s3://` access).

**Backlog (not yet built):**
- *data/sample/* — populated once Sonnet runs the sampler against real S3 raw (§8).
- A local-run entrypoint (Makefile / shell) wiring sample → Glue Docker → dbt.
- The Glue Docker invocation itself (pull `amazon/aws-glue-libs`, run `glue/*.py` over the sample).
- This addendum synced to Confluence (space `Homecredit`) via `scripts/sync_docs_to_confluence.py`.

---

## 8. Phase-1 runbook (Sonnet handover — download + sample)

**Scope for this handover:** acquire real Kaggle data → S3 dev landing → produce the slice.
**Do NOT** stand up Airflow, run AWS Glue, or touch Snowflake/Databricks in this step.

1. **Pre-reqs.** Accept the competition rules at kaggle.com/competitions/home-credit-default-risk
   (manual, one-time — download 403s otherwise). Verify Kaggle auth: `.env.dev` has
   `KAGGLE_API_TOKEN` (KGAT format) — if the `kaggle` lib won't authenticate with it, fall back to
   `KAGGLE_USERNAME`+`KAGGLE_KEY` or `~/.kaggle/kaggle.json` (chmod 600). Confirm with
   `kaggle competitions list` before the big download. AWS/S3 auth is already proven (s3fs reaches
   `s3://<S3_BUCKET_DEV>` with `.env.dev` creds, region ap-southeast-1).
2. **Download + land raw in S3.** `python bronze/download_dataset.py --env dev` — pulls the 7 CSVs
   (~2.7 GB zip; bureau_balance = 27M rows), uploads them to `s3://<S3_BUCKET_DEV>/landing/`, and
   deletes the local copies (Flow B).
3. **Verify row counts** *(do this from the downloaded files BEFORE they are deleted, or re-check
   from S3)* against README.md "Source Tables": application_train 307,511 · bureau 1,716,428 ·
   bureau_balance 27,299,925 · previous_application 1,670,214 · installments_payments 13,605,401 ·
   POS_CASH_balance 10,001,358 · credit_card_balance 3,840,312.
4. **Produce the slice (streamed from S3):**
   `python scripts/smart_sample.py --source-dir s3://<S3_BUCKET_DEV>/landing --out-dir data/sample --frac 0.015`
   Confirm the manifest's `default_rate_sample` ≈ `default_rate_full` (~0.08) and no dangling-FK
   warnings. `data/sample/` is gitignored.
5. **Report** the 7 verified row counts + manifest summary; update `PROJECT_STATUS.md` "▶ Active
   thread" with the evidence. Do **not** commit data.

---

## 9. Open integration gaps (carry forward — not yet resolved)

These are downstream couplings the Phase-1 build must address after download+sample; flagged here
so they are not missed:

- **Bronze ingest still reads the naive sample.** `bronze/ingest_bronze.py` (line 63) reads
  `data/application_train_dev_1000rows.csv` (the old head sample), **not** the smart `data/sample/`
  slice. Before the Bronze→Silver→Gold run, the dev-mode input must be repointed to the smart
  sample, or the seven `data/sample/*.csv` mapped onto the ingest path.
- **`setup.sh` regenerates `bronze/download_dataset.py`** from a heredoc (`setup.sh:705`+). The
  Flow-B edits to that file are **not** mirrored there — re-running `setup.sh` would overwrite
  them. Mirror the change or stop regenerating that file.
- **`airflow/dags/bronze_ingestion_dag.py`** (lines 37, 42) imports/calls `sample_dev_data` — a
  Phase-3 concern, but the DAG's dev path also assumes the naive sample.
- **`tests/unit/test_bronze_ingest.py`** fixtures use the `application_train_dev_1000rows.csv`
  filename — keep or migrate alongside the ingest repoint.
- **Glue Docker not yet exercised.** RAM headroom on the 2-vCPU / 4.8-GB / no-swap box is unproven
  in practice; the §3a Polars fallback exists if it chokes.
- **Snowflake DEV / Databricks SQL connectivity** for the Gold step is unverified (separate from
  this download+sample handover).

> **Promotion discipline:** when Phase 2 begins, this addendum is marked *Superseded for Silver
> location* — but kept as the historical record of how the pipeline was first validated locally.
