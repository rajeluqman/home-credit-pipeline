# Start Here — Home Credit Risk Pipeline

> Pointer page for newcomers landing on Confluence. The repo (not Confluence) is the source of
> truth — these pages are a synced read-only mirror, published via
> `scripts/sync_docs_to_confluence.py`.

## What this is
A banking credit-risk portfolio pipeline: Kaggle CSVs (7 source tables, 307,511 applications) →
AWS S3 → Glue PySpark Bronze (Delta Lake) → Silver (PII masking SHA-256, SCD2) → dbt/Snowflake
Gold (Kimball star: 3 facts + 3 dims) → BI. Orchestrated by Apache Airflow; quality-gated.

## Why it exists & what it answers
**Purpose:** turn 7 disparate Home Credit source tables into a governed Kimball star schema for a
(simulated) **credit-risk / underwriting analytics** team (consumes the BI layer, not raw CSVs),
with a GDPR-style PII-masking + SCD2 audit trail. **Business questions:** (1) default risk per
applicant, (2) bureau credit exposure, (3) installment payment punctuality, (4) demographic
change tracking for compliance audit.

**What's proven vs not:** model + transform + DQ code exists and is wired up; **run-evidence
(fact/dim row counts, DQ pass rates, KPI values, BI screenshots) not yet captured** — no metrics
fabricated (see README "Results & Evidence"). Resume "Lambda / Step Functions" claim is
**unsupported** (real orchestration: Glue + Airflow) — see INTERVIEW_GUIDE.md.

## Reading order
1. **README** — problem statement, purpose, business questions, data model, stack.
2. **AI Context (CLAUDE.md)** — governance framework, stop-gate, anti-shortcut protocol.
3. **ARCHITECTURE.md** — full layer-by-layer design.
4. **DATA_MODEL.md / DATA_DICTIONARY.md** — grain, SCD strategy, the star schema, column reference.
5. **BRD.md / DRD.md** — business + data requirements.
6. **PIPELINE_SPEC.md / DQD.md** — pipeline mechanics + quality gates.
7. **OPS_RUNBOOK.md** — how to run it.
8. **ADR-001/002/003** — Kimball star schema, PII mask order, Kimball-over-OBT sizing.
9. **INTERVIEW_GUIDE.md** — resume-claim ↔ repo-evidence reconciliation.
10. **PROJECT_STATUS.md** — current build/retrofit status.

## What's deliberately NOT synced
The `.claude/agents/` persona files, `tests/*_contract.py`, `scripts/gen_repo_map.py`,
`architecture/REPO_MAP.md`, and `learning/`/`simulation/` — AI-tooling and dev-navigation
artifacts, not onboarding documentation for a human stakeholder.
