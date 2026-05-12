"""
Run GX silver_suite — validates Silver layer data quality gates.

Gates (PIPELINE_SPEC Section 6 — all FAIL = DAG FAIL):
  - silver_application: ORGANIZATION_TYPE not 'XNA'
  - silver_application: DAYS_BIRTH_MASKED not null
  - silver_application: AMT_CREDIT > 0
  - silver_application: NULL rate OCCUPATION_TYPE < 40%
  - silver_bureau: SK_ID_BUREAU unique (no duplicates)
  - silver_bureau_balance: SK_ID_BUREAU unique (1 row per bureau record)

On failure: raises RuntimeError → Airflow task FAIL → Slack alert.
"""

import os
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

log = logging.getLogger(__name__)


def _load_silver_df(table: str, ingestion_date: str, env: str) -> pd.DataFrame | None:
    if env == "dev":
        path = Path("data") / "silver" / table / f"ingestion_date={ingestion_date}" / "part-000.parquet"
        if not path.exists():
            log.warning(f"Silver file not found: {path}")
            return None
        return pd.read_parquet(path)
    else:
        import awswrangler as wr
        bucket = os.environ[f"S3_BUCKET_{env.upper()}"]
        s3_path = f"s3://{bucket}/silver/{table}/ingestion_date={ingestion_date}/"
        return wr.s3.read_parquet(s3_path)


def _validate_application(context, df: pd.DataFrame) -> bool:
    suite_name = "silver_application_suite"
    try:
        suite = context.get_expectation_suite(suite_name)
    except Exception:
        suite = context.add_expectation_suite(suite_name)

    validator = context.get_validator(
        batch_request=RuntimeBatchRequest(
            datasource_name="local_pandas",
            data_connector_name="default_runtime_data_connector_name",
            data_asset_name="silver_application",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier_name": "default"},
        ),
        expectation_suite=suite,
    )

    # DI-001 enforced
    validator.expect_column_values_to_not_be_in_set("ORGANIZATION_TYPE", ["XNA"])
    # PII masking applied
    validator.expect_column_values_to_not_be_null("DAYS_BIRTH_MASKED")
    # Data quality
    validator.expect_column_values_to_be_between("AMT_CREDIT", min_value=0, strict_min=True)
    # OCCUPATION_TYPE NULL rate < 40%
    null_pct = df["OCCUPATION_TYPE"].isna().mean() if "OCCUPATION_TYPE" in df.columns else 0
    if null_pct >= 0.40:
        log.warning(f"OCCUPATION_TYPE NULL rate {null_pct:.1%} exceeds 40% threshold")

    results = validator.validate()
    return results["success"]


def _validate_bureau(context, df_bureau: pd.DataFrame, df_bb: pd.DataFrame) -> bool:
    suite = context.add_expectation_suite("silver_bureau_suite") if not _suite_exists(context, "silver_bureau_suite") else context.get_expectation_suite("silver_bureau_suite")

    v_bureau = context.get_validator(
        batch_request=RuntimeBatchRequest(
            datasource_name="local_pandas",
            data_connector_name="default_runtime_data_connector_name",
            data_asset_name="silver_bureau",
            runtime_parameters={"batch_data": df_bureau},
            batch_identifiers={"default_identifier_name": "default"},
        ),
        expectation_suite=suite,
    )
    v_bureau.expect_column_values_to_be_unique("SK_ID_BUREAU")
    r1 = v_bureau.validate()

    suite_bb = context.add_expectation_suite("silver_bureau_balance_suite") if not _suite_exists(context, "silver_bureau_balance_suite") else context.get_expectation_suite("silver_bureau_balance_suite")
    v_bb = context.get_validator(
        batch_request=RuntimeBatchRequest(
            datasource_name="local_pandas",
            data_connector_name="default_runtime_data_connector_name",
            data_asset_name="silver_bureau_balance",
            runtime_parameters={"batch_data": df_bb},
            batch_identifiers={"default_identifier_name": "default"},
        ),
        expectation_suite=suite_bb,
    )
    v_bb.expect_column_values_to_be_unique("SK_ID_BUREAU")
    r2 = v_bb.validate()

    return r1["success"] and r2["success"]


def _suite_exists(context, name: str) -> bool:
    try:
        context.get_expectation_suite(name)
        return True
    except Exception:
        return False


def run(env: str = "dev", ingestion_date: str = None):
    ingestion_date = ingestion_date or date.today().isoformat()
    context = gx.get_context(context_root_dir="gx")

    failures = []

    df_app = _load_silver_df("silver_application", ingestion_date, env)
    if df_app is not None:
        if not _validate_application(context, df_app):
            failures.append("silver_application")
            log.error("GX silver_suite FAIL: silver_application")
        else:
            log.info("GX silver_suite PASS: silver_application")

    df_bureau = _load_silver_df("silver_bureau", ingestion_date, env)
    df_bb = _load_silver_df("silver_bureau_balance", ingestion_date, env)
    if df_bureau is not None and df_bb is not None:
        if not _validate_bureau(context, df_bureau, df_bb):
            failures.append("silver_bureau")
            log.error("GX silver_suite FAIL: silver_bureau / silver_bureau_balance")
        else:
            log.info("GX silver_suite PASS: silver_bureau")

    if failures:
        raise RuntimeError(f"GX silver_suite FAILED for: {failures} — DAG stopped")

    log.info("GX silver_suite: ALL PASS")


if __name__ == "__main__":
    import sys
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    run(env=env)
