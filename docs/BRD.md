# BRD: Home Credit Risk Pipeline
> Document  : Business Requirements Document v1.0
> Phase     : 1 — BRD
> Status    : SIGNED OFF
> Owner     : BA (Business Analyst)
> Signed by : BA ✅ | PO ✅ | PM ✅ | DQS ✅
> Date      : 2026-05-12

---

## 1. Business Context

Home Credit serves unbanked and underbanked populations who lack traditional credit histories.
The organisation relies on alternative data (bureau records, payment histories, previous applications)
to assess creditworthiness. Without a structured data pipeline, risk analysts cannot efficiently
segment applicants, track portfolio health, or audit PII handling for compliance.

**Business Problem:**
Build a scalable, auditable data pipeline that ingests 7 source tables (300k+ loan application
records), applies data quality gating and PII masking, and surfaces credit risk KPIs in a
governed Gold layer — enabling the Risk Team to identify default-risk segments and the
Compliance Team to demonstrate GDPR-aligned data handling.

**Resume Entry Being Proven:**
> "Engineered a scalable ingestion pipeline integrating 300k+ credit records from 7 disparate
> source tables with full schema alignment, automated data quality gating via Great Expectations,
> PII masking (SHA-256), and SCD Type 2 historical tracking for compliance."

---

## 2. Stakeholders

| # | Stakeholder       | Role              | Primary Data Need                                       | Priority |
|---|-------------------|-------------------|---------------------------------------------------------|----------|
| 1 | Risk Team         | Primary consumer  | Default rate by segment (loan type, income, employment) | High     |
| 2 | Compliance        | Audit & oversight | PII masking evidence + SCD Type 2 audit trail           | High     |
| 3 | Portfolio Mgmt    | Secondary consumer| Loan portfolio health KPIs, credit amount distribution  | Medium   |
| 4 | Data Engineering  | Pipeline owner    | Schema alignment, data quality checks, pipeline uptime  | High     |

---

## 3. Business Requirements — MoSCoW Priority

### Must Have (blocking downstream, Phase 1 scope)

| # | Requirement | Business Value | Success Metric |
|---|-------------|---------------|----------------|
| BR-01 | Ingest all 7 source CSV tables from Kaggle to Bronze layer | Baseline for all analytics | Row count match: Bronze = source ± 0 |
| BR-02 | Apply PII masking (SHA-256) on quasi-identifiers (DAYS_BIRTH, DAYS_EMPLOYED) before Silver layer | GDPR alignment, no raw PII in analytics | GX check: masked ≠ original values |
| BR-03 | Implement SCD Type 2 for dim_applicant (start_date, end_date, is_current) | Compliance audit trail for applicant history | is_current=True count = unique SK_ID_CURR |
| BR-04 | Calculate Default Rate KPI in Gold layer (fact_loan_application) | Core risk metric for Risk Team | Formula verified vs manual SQL count |
| BR-05 | Great Expectations validation suite at Bronze, Silver, Gold layers | Data quality gating — no bad data downstream | GX HTML report generated per layer |
| BR-06 | Quarantine bad rows — do not block pipeline for non-critical failures | Pipeline resilience | Quarantine table populated for HIGH/MEDIUM severity |

### Should Have (important, not blocking Phase 1 sign-off)

| # | Requirement | Business Value |
|---|-------------|---------------|
| BR-07 | Bureau delinquency rate KPI (integration of bureau.csv) | Enriched risk view per applicant |
| BR-08 | Airflow DAG orchestration with Slack pass/fail alerts | Operational visibility |
| BR-09 | Income-to-Credit Ratio metric per segment | Risk signal beyond default flag |

### Could Have (Phase 2 backlog)

| # | Requirement |
|---|-------------|
| BR-10 | Previous application count per applicant (fact_bureau_credit enrichment) |
| BR-11 | Credit card balance trend analysis (credit_card_balance.csv integration) |
| BR-12 | POS cash balance delinquency trend |

### Won't Have (out of scope — explicitly excluded)

| Exclusion | Reason |
|-----------|--------|
| ML prediction model | Bukan data engineering scope. Resume entry is pipeline, not ML. |
| Real-time streaming / Kafka | Source data is static CSV — CDC simulation via upsert, not streaming |
| Power BI dashboard development | Consumer layer — pipeline ends at Gold/Snowflake |
| New tool suggestions outside resume stack | Stack boundary is hard limit per playbook |

---

## 4. KPIs — Explicit Formulas (BA enforced)

| # | KPI | Explicit Formula | Grain | Frequency | Source Table |
|---|-----|-----------------|-------|-----------|-------------|
| KPI-01 | Default Rate | `COUNT(SK_ID_CURR WHERE TARGET=1) / COUNT(SK_ID_CURR) * 100` | Overall + per loan type | Daily | fact_loan_application |
| KPI-02 | Avg Credit Amount by Loan Type | `AVG(AMT_CREDIT) GROUP BY NAME_CONTRACT_TYPE` | Per loan type | Daily | fact_loan_application |
| KPI-03 | Bureau Delinquency Rate | `COUNT(SK_ID_BUREAU WHERE CREDIT_DAY_OVERDUE > 0) / COUNT(SK_ID_BUREAU) * 100` | Overall | Daily | fact_bureau_credit |
| KPI-04 | Income-to-Credit Ratio | `AVG(AMT_INCOME_TOTAL / NULLIF(AMT_CREDIT, 0))` | Per segment | Daily | fact_loan_application + dim_applicant |
| KPI-05 | Avg Days Employed (masked proxy) | `AVG(DAYS_EMPLOYED_MASKED_HASH)` — note: value is hashed, metric is existence/presence | Per income bracket | Weekly | dim_applicant |

> **BA Rule enforced:** KPI-05 note — DAYS_EMPLOYED is SHA-256 masked. Numeric computation not
> possible post-masking. KPI-05 is scoped to presence validation only, not numeric aggregation.
> PO accepted this limitation. DQS to validate masking in Silver GX suite.

---

## 5. Data Sources Overview

| # | File | Rows (approx) | Description | Pipeline Layer |
|---|------|---------------|-------------|---------------|
| 1 | application_train.csv | 307,511 | Primary loan applications — TARGET variable | Bronze → Silver → Gold (fact_loan_application, dim_applicant) |
| 2 | bureau.csv | 1,716,428 | Bureau credit records per applicant | Bronze → Silver → Gold (fact_bureau_credit) |
| 3 | bureau_balance.csv | 27,299,925 | Monthly bureau balance statuses | Bronze → Silver (supporting bureau aggregation) |
| 4 | previous_application.csv | 1,670,214 | Previous loan applications at Home Credit | Bronze → Silver (Should Have — Phase 2 Gold) |
| 5 | installments_payments.csv | 13,605,401 | Installment payment records | Bronze → Silver → Gold (fact_installment_payment) |
| 6 | POS_CASH_balance.csv | 10,001,358 | POS and cash loan balance history | Bronze (Could Have integration) |
| 7 | credit_card_balance.csv | 3,840,312 | Credit card balance history | Bronze (Could Have integration) |

> **DQS Note:** bureau_balance.csv at 27M rows is the largest file. AWS Glue DPU usage must
> be monitored. Dev uses 1000 rows from application_train only — bureau_balance deferred to staging.

---

## 6. Business Rules

| # | Rule | Owner | Enforced At |
|---|------|-------|-------------|
| BR-RULE-01 | TARGET column: 0 = repaid, 1 = defaulted. NULL TARGET rows = quarantine. | DQS | Silver GX |
| BR-RULE-02 | SK_ID_CURR must be unique in application_train (1 application per row) | DQS | Bronze GX |
| BR-RULE-03 | bureau.SK_ID_CURR must exist in application_train (referential integrity) | DQS | Silver GX |
| BR-RULE-04 | AMT_CREDIT > 0 always. Zero or negative = quarantine. | DQS | Silver GX |
| BR-RULE-05 | DAYS_BIRTH and DAYS_EMPLOYED masked via SHA-256 before Silver write | DE | Glue Silver job |
| BR-RULE-06 | SCD Type 2: only one is_current=True record per SK_ID_CURR in dim_applicant | AE | dbt Gold |

---

## 7. Out of Scope

- Real-time data ingestion (source is static CSV, no CDC available)
- ML model development or scoring pipeline
- Power BI dashboard build (Compliance and Risk Teams build their own views)
- New tools not in resume stack (Docker, MLflow not in this project's stack boundary)
- bureau_balance.csv Gold integration (deferred — 27M rows, DPU risk)

---

## 8. Sign-off Gate — Phase 1

### Agent Reviews

**BA — Business Analyst:**
BRD requirement BR-05 checked — KPI formulas are explicit with NULLIF guard (KPI-04).
KPI-05 has been flagged and scoped down — cannot aggregate hashed values numerically.
All requirements have clear business justification. Scope out of ML is correct.
`BA ✅ APPROVED — BRD v1.0 meets business requirements standard.`

**PO — Product Owner:**
Must Have (BR-01 to BR-06) are correctly blocked as Phase 1 critical.
Should Have (BR-07 to BR-09) correctly deferred — not blocking Bronze/Silver build.
Could Have (BR-10 to BR-12) correctly Phase 2 backlog.
ML, streaming, Power BI dev — Won't Have confirmed.
bureau_balance.csv Gold integration deferred — correct call given DPU risk.
`PO ✅ APPROVED — Scope is clean. Priorities are realistic for Codespace constraint.`

**DQS — Data Quality Steward:**
Data quality requirements are explicit (BR-05, BR-06, BR-RULE-01 to BR-RULE-06).
GX suite per layer confirmed in BR-05. Quarantine strategy in BR-06.
KPI-05 masking limitation flagged and accepted. SHA-256 validation scope clear.
DQS Note on bureau_balance.csv row count acknowledged.
`DQS ✅ APPROVED — Data quality scope adequate for Phase 1. Will define GX expectations in Phase 2 DRD.`

**PM — Project Manager:**
All 4 sign-offs received. No blockers remain.
Next phase: Phase 2 — DRD (agents: BA, DA, SDE, DPE, DQS).
Hard blockers for Phase 2 → Phase 3 gate are clear in CLAUDE.md.
`PM ✅ APPROVED — Phase 1 BRD complete. Proceeding to Phase 2.`

---

=== SIGN OFF: BRD v1.0 ===
BA  ✅ — BRD v1.0 approved. KPI formulas explicit. Scope correct.
PO  ✅ — Priorities clean. Won't Have list enforced.
DQS ✅ — DQ requirements adequate. GX scope clear.
PM  ✅ — No blockers. Gate passed.
Status : APPROVED
Action : Proceed to Phase 2 — DRD
