# Debate Log — Phase 1: BRD
> Reconstructed from Phase 1 decisions. Not a real-time transcript — decisions were
> pre-derived from dataset context. Agents: BA, PO, PM, DQS.
> Always active: FinOps (11), Scope Guardian (12).
> Date: 2026-05-12 | Status: All debates resolved, BRD signed off.

---

## Pre-Phase Announcement

**MCP ORCHESTRATOR:**
> Phase 1 tools available: Read/Write docs/BRD.md, sign-offs/, PROJECT_STATUS.md.
> No cloud tools needed. No MCP server calls this phase.

**FinOps:**
> Phase 1 model assignments approved.
> BA, PO, DQS, PM → Sonnet. No Haiku tasks this phase.
> Est. token cost: ~$0.02. Acceptable.

---

## Debate 1 — KPI-05: Boleh ke aggregate DAYS_EMPLOYED selepas SHA-256?

**Round 1**

**BA:**
> Draft KPI-05 aku letak: "Avg Days Employed per income bracket — AVG(DAYS_EMPLOYED) GROUP BY income_bracket."
> Ini useful untuk risk profiling. Makin lama employed, makin rendah risk. Standard metric.

**DQS:**
> Tunggu dulu. DAYS_EMPLOYED kita mask dengan SHA-256 sebelum Silver.
> SHA-256 output dia hex string — contoh: `a3f9c2d...`. Kau nak AVG() string?
> Mathematically impossible. Database akan throw error atau return NULL.

**BA:**
> Betul. Aku terlepas pandang. SHA-256 destroys numeric comparability.
> Kita tak boleh compute AVG, MIN, MAX, atau sebarang numeric aggregate
> pada nilai yang dah di-hash.

**PO:**
> So option kita:
> Option A — Remove KPI-05 completely.
> Option B — Tukar metric kepada presence validation (is masked column populated?).
> Option C — Mask column lain, jangan mask DAYS_EMPLOYED (kalau business value justify).

**DQS:**
> Option C out of scope — DAYS_BIRTH dan DAYS_EMPLOYED explicitly listed dalam
> PII masking strategy. Boleh deduce umur dan employment status. Kena mask.

**BA:**
> Option B lebih realistic. KPI-05 jadi: "Masked column presence check —
> DAYS_EMPLOYED_MASKED is NOT NULL dan != original value."
> Bukan analytics KPI sebenar, tapi jadi DQ validation proof untuk compliance.

**PO:**
> Setuju. KPI-05 stay dalam BRD sebagai compliance validation metric,
> bukan analytics KPI. Label dia jelas dalam doc.

**PM:**
> Round 1 — resolved. No escalation needed.
> Decision: KPI-05 scoped to presence/masking validation only. Numeric aggregation out.

**Outcome:** KPI-05 redefined. AVG(DAYS_EMPLOYED) removed. SHA-256 masking limitation documented.
**Rounds used:** 1/3

---

## Debate 2 — bureau_balance.csv: Perlu masuk Gold layer ke?

**Round 1**

**BA:**
> bureau_balance.csv ada monthly status per bureau credit record.
> Kalau kita integrate ke Gold, kita boleh bina trend analysis —
> berapa bulan applicant ada overdue status sebelum apply loan.
> Business value: high. Risk Team suka time-series delinquency data.

**DQS:**
> Row count: 27,299,925 rows. Dua puluh tujuh juta.
> AWS Glue free tier: 1M DPU-second.
> bureau_balance Silver transform + Gold load = minimum 3-4 Glue jobs,
> masing-masing dengan shuffle operations sebab joins dengan bureau.csv.
> Satu job untuk 27M rows boleh habis 200k-400k DPU-second.
> Kita ada 1M limit untuk SEMUA phases. bureau_balance alone boleh makan 40% budget.

**FinOps (intervenes):**
> DQS correct. bureau_balance.csv Gold integration = high DPU risk.
> Saya enforce cost cap: jangan commit ke Gold integration kalau ada DPU risk >30% budget.
> Defer ke Phase 2 atau decommission dari scope.

**PO:**
> Business value ada — tapi bukan Must Have untuk Phase 1 proof.
> Resume entry kita: "300k+ credit records dari 7 source tables."
> Bronze ingest dia — check. Transform ke Gold — tidak perlu untuk Phase 1 proof.
> Defer Gold integration. Bronze sahaja untuk bureau_balance.

**BA:**
> Setuju. Bronze ingest = schema alignment proof (resume entry covered).
> Gold integration = Could Have, Phase 2 backlog.

**PM:**
> Round 1 — resolved.
> Decision: bureau_balance.csv → Bronze (ingest only). Gold integration deferred.

**Outcome:** bureau_balance.csv Bronze ingest ✅. Silver/Gold deferred — DPU risk too high.
**Rounds used:** 1/3

---

## Debate 3 — Airflow + Slack: Must Have atau Should Have dalam BRD?

**Round 1**

**BA:**
> Airflow orchestration dan Slack alerts — aku letak dalam Must Have.
> Kalau pipeline tak ada scheduling, staging environment tak boleh jalan automated.
> Business requirement: pipeline mesti run daily untuk KPIs refresh.

**PO:**
> Objection. BRD tracks business requirements, bukan implementation decisions.
> Airflow adalah tool choice — implementation layer.
> Business requirement yang betul: "Pipeline mesti run on schedule dan notify bila fail."
> Cara kita fulfill tu (Airflow + Slack) = ARCHITECTURE.md decision, bukan BRD.
> In BRD, letak requirement: "Automated scheduling + failure alerting."
> Should Have — sebab manual trigger pun boleh fulfill dev environment.

**BA:**
> Fair. BA agreed — business requirement is the outcome (scheduled runs, fail alerts),
> bukan the specific tool. Airflow + Slack → Should Have dalam BRD,
> Must Have dalam PIPELINE_SPEC.md.

**DQS:**
> Setuju. Dari DQ perspective — Airflow matters untuk GX validation scheduling.
> Tapi GX boleh run manually dalam dev. Should Have correct.

**PM:**
> Round 1 — resolved. PO point valid.
> Decision: Automated scheduling + alerting = Should Have dalam BRD.
> Tool specifics (Airflow, Slack) = ARCHITECTURE.md.

**Outcome:** BR-08 correctly classified as Should Have. Tool choice deferred to Phase 3.
**Rounds used:** 1/3

---

## Debate 4 — ML Prediction Pipeline: In scope ke?

**Round 1**

**BA:**
> Kaggle competition dataset ada TARGET column — binary classification.
> Should we include a prediction pipeline in scope?
> Boleh demonstrate end-to-end: ingest → clean → model → score.
> Business value: obvious. Risk Team nak probability of default, bukan just binary flag.

**Scope Guardian (VETO — immediate intervention):**
> STOP.
> Resume entry yang kita nak prove: "data engineering pipeline."
> ML pipeline = Data Scientist / ML Engineer scope.
> Tools dalam resume ada MLflow — tapi portfolio ini bukan ML portfolio.
> Kalau include ML, recruiter confused: ini DE portfolio ke DS portfolio?
> Scope in ML = dilute DE focus. VETO.

**PO:**
> Scope Guardian correct. Won't Have.
> "Nice to have" dalam DS context, tapi actively harmful untuk DE portfolio focus.

**BA:**
> Accepted. Won't Have. Business value ada tapi out of scope untuk portfolio proof.

**PM:**
> Scope Guardian veto accepted. No debate rounds counted — immediate resolution.
> Decision: ML prediction pipeline = Won't Have.

**Outcome:** ML out of scope. Won't Have locked. Scope Guardian veto stands.
**Rounds used:** 0/3 (Scope Guardian veto = immediate, no rounds)

---

## Debate 5 — KPI-04 Formula: Division by Zero Risk

**Round 1**

**DQS:**
> KPI-04 draft: `AVG(AMT_INCOME_TOTAL / AMT_CREDIT)`.
> Data quality issue — what if AMT_CREDIT = 0?
> Business rule BR-04 kata AMT_CREDIT > 0, tapi quarantine happens AFTER compute.
> Kalau sequence salah, division by zero mungkin berlaku dalam Gold dbt model.

**BA:**
> Good catch. Kena NULLIF guard:
> `AVG(AMT_INCOME_TOTAL / NULLIF(AMT_CREDIT, 0))`
> NULLIF converts AMT_CREDIT = 0 to NULL, AVG ignores NULLs automatically.
> Formula selamat.

**PO:**
> Setuju. Update formula. Ini correct engineering practice, bukan scope change.

**DQS:**
> Confirmed. Juga pastikan GX expectation untuk AMT_CREDIT:
> `expect_column_values_to_be_between(min_value=1)` — enforce positive values.
> Quarantine rows where AMT_CREDIT <= 0 before KPI compute.

**PM:**
> Round 1 — resolved.
> Decision: KPI-04 formula updated dengan NULLIF guard. GX expectation noted untuk Phase 2.

**Outcome:** KPI-04 formula corrected. DQS to include GX expectation in Phase 2 DRD.
**Rounds used:** 1/3

---

## Debate 6 — Should Have items: Bureau Delinquency Rate (KPI-03)

**Round 1**

**BA:**
> KPI-03: Bureau Delinquency Rate = COUNT(CREDIT_DAY_OVERDUE > 0) / COUNT(*).
> Ini require bureau.csv integration ke Gold — fact_bureau_credit.
> Grain: 1 row = 1 bureau record. SK_ID_BUREAU unique key.

**PO:**
> Bureau integration ada dalam scope — 3 fact tables termasuk fact_bureau_credit.
> Ini pre-locked. KPI-03 stays.

**DQS:**
> Flag: bureau.csv ada 1.7M rows. Referential integrity check penting —
> bureau.SK_ID_CURR MESTI ada dalam application_train.SK_ID_CURR.
> Kalau ada orphan bureau records (applicant tak ada dalam application_train),
> KPI-03 akan overcount delinquency.
> Business rule: BR-RULE-03 — bureau FK check wajib dalam Silver GX.

**BA:**
> Agreed. Add BR-RULE-03 dalam BRD business rules section.
> KPI-03 formula valid, tapi dependent on FK integrity.

**PM:**
> Round 1 — resolved. BR-RULE-03 added.
> Decision: KPI-03 in scope. DQS to enforce FK check in Silver GX suite (Phase 2).

**Outcome:** KPI-03 confirmed in scope. BR-RULE-03 added to BRD business rules.
**Rounds used:** 1/3

---

## Sign-off Gate — PM Facilitation

**PM:**
> Semua 6 debates resolved. Round count: max 1/3 per topic. No escalation ke human.
> Scope Guardian intervened sekali (Debate 4 — ML) — veto accepted.
> FinOps intervened sekali (Debate 2 — bureau_balance DPU) — cost cap enforced.
>
> Calling for final sign-off:

**BA:**
> BRD reflects correct business requirements. KPI formulas explicit.
> KPI-05 scoped correctly. Won't Have list clear.
> **BA ✅ APPROVED**

**PO:**
> Scope is clean. Must Have realistic for Codespace + free tier.
> bureau_balance Gold integration correctly deferred.
> ML correctly excluded.
> **PO ✅ APPROVED**

**DQS:**
> Data quality requirements covered in BR-05, BR-06, BR-RULE-01 to BR-RULE-06.
> GX expectations flagged untuk Phase 2 definition.
> SHA-256 masking limitation documented.
> **DQS ✅ APPROVED**

**PM:**
> All agents approved. No blockers outstanding.
> Proceeding to Phase 2 — DRD.
> **PM ✅ APPROVED**

---

=== SIGN OFF: BRD v1.0 ===
BA  ✅ — Approved. 6 debates, 0 escalations.
PO  ✅ — Approved. Scope clean, Won't Have enforced.
DQS ✅ — Approved. DQ requirements clear.
PM  ✅ — Gate passed. No blockers.
Status : APPROVED
Action : Phase 2 — DRD. Agents: BA, DA, SDE, DPE, DQS, PM.
