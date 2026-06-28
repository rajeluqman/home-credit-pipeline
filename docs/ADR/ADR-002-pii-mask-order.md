# ADR-002: PII Masking Order — Sentinel-Null Before SHA-256

Status: Accepted
Date  : 2026-06-28 (backfilled during pipeline-retrofit governance pass; rationale
        reconstructed from existing code/README, owner confirm)
Owner : Data Quality Steward + Senior Data Engineer

## Context
`DAYS_BIRTH` and `DAYS_EMPLOYED` are masked via SHA-256 for GDPR-style compliance
(`silver/transforms.py`, `glue/glue_silver_application.py`). `DAYS_EMPLOYED` carries a known
Home Credit dataset anomaly: unemployed/retired applicants are encoded with the sentinel value
`365243` instead of NULL. README.md already documents the rule informally ("PII Masking
Strategy" table, `365243 → NULL first (DI-002), THEN SHA-256`) — this ADR makes the *why*
and the *test* explicit and binding rather than leaving it as a single README line.

## Decision
Masking order is **sentinel-substitution BEFORE hashing**, never the reverse:
1. `365243 → NULL` (DI-002, applies to `DAYS_EMPLOYED` only)
2. `hashlib.sha256(str(value).encode()).hexdigest()` on the remaining non-null values

## Why this order, specifically
If SHA-256 ran first, every unemployed/retired applicant's sentinel `365243` would hash to
the **same fixed digest** — turning a data-quality sentinel into a leaked categorical signal
(every row with that exact hash is provably "unemployed/retired"), defeating the purpose of
masking. Nulling the sentinel first removes the value from the hashed domain entirely, so no
inference is possible from the masked column.

## Consequences
(+) GX silver_suite gate checks the inverse condition directly:
    `DAYS_EMPLOYED_MASKED not in sha256('365243')` (`gx/run_silver_suite.py` does the PII/dedup
    checks — see `docs/DQD.md` for the full silver gate list)
(+) `silver/transforms.py` (local pandas mirror) and the Glue PySpark job
    (`glue/glue_silver_application.py`) must implement the SAME order — any future Glue
    rewrite must replicate `silver/transforms.py`'s order, not just its output columns
(-) An out-of-order masking bug is silent (column name and type are unchanged; only the
    *meaning* of the masked value differs) — this is exactly why the order needs a named ADR
    and a quality gate, not just a code comment

## Alternatives Rejected
- Mask first, then sentinel-check: rejected — defeats the masking's purpose (see above).
- Drop sentinel rows entirely instead of nulling: rejected — would discard a real population
  segment (unemployed/retired applicants) from `dim_applicant`, breaking BRD KPI coverage.
