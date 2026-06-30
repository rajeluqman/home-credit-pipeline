#!/usr/bin/env python3
"""Stack + scope boundary contract — deterministic gate over this repo's locked stack.

Ported from creative_intelligence_lab's tests/boundary_contract.py pattern, retargeted to
THIS repo's real rejected-tech axis (docs/ARCHITECTURE.md "CRITICAL Constraint"):
  - Spark is allowed ONLY inside glue/*.py (AWS Glue is the one sanctioned PySpark surface)
  - Databricks is query-only (Serverless SQL) — no databricks SDK / job-cluster libraries
    anywhere, including glue/ (Glue jobs use Spark directly, never the Databricks SDK)
  - No new ingestion connector beyond the Kaggle Competition API (no Fivetran/Airbyte/etc.)
  - dbt profile target must stay Snowflake (this repo's Gold compute, unlike CIL's DuckDB)

Stdlib only ($0, no deps). Exit 0 = contract holds. Exit 1 = hard violation.

Rules:
  ST1  no `pyspark` import outside glue/*.py (Spark only inside Glue jobs)
  ST2  no `databricks` SDK / job-cluster import anywhere (query-only via Serverless SQL,
       which this repo never touches from Python — BI/SQL client only)
  ST3  no Fivetran/Airbyte/connector-platform dependency (Kaggle API is the sole ingestion path)
  ST4  dbt profile adapter `type:` must be `snowflake` (never duckdb/bigquery/postgres —
       this repo's Gold compute is locked to Snowflake, the inverse constraint of CIL's
       DuckDB-only rule, since the two repos intentionally use different stacks)

Run:  python tests/boundary_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PY_GLOBS_ALL = ["silver/*.py", "airflow/dags/*.py", "gx/*.py", "tests/unit/*.py"]
# Spark is sanctioned in glue/ (Glue jobs) AND bronze/ (delta-spark/Delta Lake writes to S3 —
# README.md "Bronze — Delta Lake on S3" + ingest_bronze.py's ingest_cloud() requires a
# SparkSession via delta-spark; this is a real doc gap vs ARCHITECTURE.md's "Silver = AWS
# Glue (Spark) SAHAJA" wording — flagged in PROJECT_STATUS.md / INTERVIEW_GUIDE.md for an
# ARCHITECTURE.md correction, not silenced here).
PY_GLOBS_GLUE = ["glue/*.py", "bronze/*.py"]
REQUIREMENTS_FILES = ["requirements.txt"]
PROFILE_FILES = ["dbt_home_credit/profiles.yml"]

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_.]+)")
REQ_LINE_RE = re.compile(r"^([A-Za-z0-9_.-]+)")

GLUE_ONLY_DENY: dict[str, str] = {
    "pyspark": "ARCHITECTURE.md CRITICAL Constraint — Spark ONLY inside glue/ jobs",
}
ALWAYS_DENY: dict[str, str] = {
    "databricks": "ARCHITECTURE.md CRITICAL Constraint — Databricks is Serverless SQL query-only, no SDK/job-cluster usage from pipeline code",
    "fivetran": "no ingestion connector beyond the Kaggle Competition API",
    "airbyte": "no ingestion connector beyond the Kaggle Competition API",
}


def _hits(module: str, deny: dict[str, str]) -> str | None:
    parts = module.lower().split(".")
    for i in range(1, len(parts) + 1):
        prefix = ".".join(parts[:i])
        if prefix in deny:
            return deny[prefix]
    return None


def _scan_python(path: Path, errors: list[str], deny: dict[str, str]) -> None:
    rel = path.relative_to(REPO)
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        m = IMPORT_RE.match(line)
        if not m:
            continue
        reason = _hits(m.group(1), deny)
        if reason:
            errors.append(f"{rel}:{lineno}: banned import '{m.group(1)}' — {reason}")


def _scan_requirements(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(REPO)
    deny = {**ALWAYS_DENY}
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = REQ_LINE_RE.match(line)
        if not m:
            continue
        pkg = m.group(1).lower().replace("-", "_")
        reason = deny.get(pkg)
        if reason:
            errors.append(f"{rel}:{lineno}: banned dependency '{m.group(1)}' — {reason}")


def _scan_profile_adapter(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(REPO)
    type_re = re.compile(r"^\s*type:\s*(\S+)")
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        m = type_re.match(line)
        if m and m.group(1) != "snowflake":
            errors.append(
                f"{rel}:{lineno}: dbt profile adapter type '{m.group(1)}' != 'snowflake' — "
                "this repo's Gold compute is locked to Snowflake"
            )


def check() -> list[str]:
    errors: list[str] = []

    for pattern in PY_GLOBS_ALL:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, {**GLUE_ONLY_DENY, **ALWAYS_DENY})

    for pattern in PY_GLOBS_GLUE:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, ALWAYS_DENY)  # pyspark IS allowed here

    for name in REQUIREMENTS_FILES:
        path = REPO / name
        if path.exists():
            _scan_requirements(path, errors)

    for name in PROFILE_FILES:
        path = REPO / name
        if path.exists():
            _scan_profile_adapter(path, errors)

    return errors


def main() -> int:
    errors = check()
    if errors:
        print(f"\n❌ BOUNDARY CONTRACT FAILED — {len(errors)} violation(s):", file=sys.stderr)
        for e in sorted(set(errors)):
            print(f"   • {e}", file=sys.stderr)
        print("\n   See docs/ARCHITECTURE.md CRITICAL Constraint. Fix before proceeding.", file=sys.stderr)
        return 1
    print("✅ boundary contract OK (Glue-only Spark, Databricks query-only, Snowflake-locked Gold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
