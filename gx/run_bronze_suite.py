"""
Run GX bronze_suite against Bronze parquet files (dev: local, cloud: S3).

Gates (PIPELINE_SPEC Section 6):
  - Row count > 0 per table (WARN — pipeline continues)
  - PK column NOT NULL (quarantine already handled upstream, just log)

On failure: log warning. Pipeline continues (quarantine path already written).
"""

import os
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

log = logging.getLogger(__name__)


BRONZE_TABLES = {
    "application_train": "SK_ID_CURR",
    "bureau": "SK_ID_BUREAU",
    "bureau_balance": "SK_ID_BUREAU",
    "previous_application": "SK_ID_PREV",
    "installments_payments": "SK_ID_PREV",
    "POS_CASH_balance": "SK_ID_PREV",
    "credit_card_balance": "SK_ID_PREV",
}


def _load_bronze_df(table: str, ingestion_date: str, env: str) -> pd.DataFrame | None:
    if env == "dev":
        path = Path("data") / "bronze" / table / f"ingestion_date={ingestion_date}" / "part-000.parquet"
        if not path.exists():
            log.warning(f"Bronze file not found: {path}")
            return None
        return pd.read_parquet(path)
    else:
        import awswrangler as wr
        bucket = os.environ[f"S3_BUCKET_{env.upper()}"]
        s3_path = f"s3://{bucket}/bronze/{table}/ingestion_date={ingestion_date}/"
        return wr.s3.read_parquet(s3_path)


def _validate_table(context, df: pd.DataFrame, table: str, pk_col: str) -> bool:
    suite_name = f"bronze_{table}_suite"

    try:
        suite = context.get_expectation_suite(suite_name)
    except Exception:
        suite = context.add_expectation_suite(suite_name)

    validator = context.get_validator(
        batch_request=RuntimeBatchRequest(
            datasource_name="local_pandas",
            data_connector_name="default_runtime_data_connector_name",
            data_asset_name=table,
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier_name": "default"},
        ),
        expectation_suite=suite,
    )

    validator.expect_table_row_count_to_be_between(min_value=1)
    validator.expect_column_values_to_not_be_null(pk_col)

    results = validator.validate()
    passed = results["success"]
    if not passed:
        log.warning(f"GX bronze_suite WARN for {table}: {results['statistics']}")
    else:
        log.info(f"GX bronze_suite PASS for {table}")
    return passed


def run(env: str = "dev", ingestion_date: str = None):
    ingestion_date = ingestion_date or date.today().isoformat()
    context = gx.get_context(context_root_dir="gx")

    results = {}
    for table, pk_col in BRONZE_TABLES.items():
        df = _load_bronze_df(table, ingestion_date, env)
        if df is None:
            results[table] = "SKIPPED"
            continue
        passed = _validate_table(context, df, table, pk_col)
        results[table] = "PASS" if passed else "WARN"

    passed_count = sum(1 for v in results.values() if v == "PASS")
    log.info(f"GX bronze_suite complete: {passed_count}/{len(BRONZE_TABLES)} PASS | {results}")
    return results


if __name__ == "__main__":
    import sys
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    run(env=env)
