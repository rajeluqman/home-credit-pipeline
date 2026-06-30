"""Silver (S3 staging, full 58.4M-row scale) -> Snowflake HOME_CREDIT_RISK.STAGING loader.

Gate-2-scoped (docs/ADDENDUM-A_local-dev-smart-sampling.md Sec 5): manual COPY INTO from an
external stage, not auto-ingest Snowpipe -- chosen over a second Snowpipe (owner decision,
2026-06-30) specifically to avoid doubling the persistent-infra/teardown surface while
ADR-004's dev-Snowpipe teardown is still open. Scoped to the 4 silver tables
dbt_home_credit/models/sources.yml actually declares (silver_application, silver_bureau,
silver_bureau_balance, silver_installments) -- same scope decision made for the dev Snowpipe
in the Gate-1 thread.

Reuses the proven Gate-1 COPY INTO pattern: ingestion_date is a Spark Hive partition column,
not present inside the Parquet file content, so it is reconstructed from METADATA$FILENAME;
all source Parquet field keys are upper-case except ingestion_ts (lower-case).

Pre-requisites (both already done, see PROJECT_STATUS.md "Phase 2 execution" thread):
  - HOME_CREDIT_SILVER_INT's STORAGE_ALLOWED_LOCATIONS includes s3://home-credit-risk-staging/silver/
  - snowflake_silver_loader's IAM policy grants read on home-credit-risk-staging/silver/*
"""

import logging
import os

import snowflake.connector
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

STAGE_FQN = "HOME_CREDIT_RISK.STAGING.SILVER_STAGE"
STAGE_URL = "s3://home-credit-risk-staging/silver/"
STORAGE_INTEGRATION = "HOME_CREDIT_SILVER_INT"
FILE_FORMAT_FQN = "HOME_CREDIT_RISK.DEV.PARQUET_FORMAT"

# (column, snowflake_type, source_parquet_key) -- matches the live schema read off the
# real Glue Silver Delta output via PySpark+S3A this session, and the existing DEV table
# DDL column-for-column (DESCRIBE TABLE HOME_CREDIT_RISK.DEV.<table>).
TABLES = {
    "SILVER_APPLICATION": {
        "prefix": "silver_application",
        "expected_rows": 307_511,
        "columns": [
            ("SK_ID_CURR", "NUMBER", "SK_ID_CURR"),
            ("TARGET", "NUMBER", "TARGET"),
            ("NAME_CONTRACT_TYPE", "VARCHAR", "NAME_CONTRACT_TYPE"),
            ("AMT_CREDIT", "FLOAT", "AMT_CREDIT"),
            ("AMT_ANNUITY", "FLOAT", "AMT_ANNUITY"),
            ("AMT_INCOME_TOTAL", "FLOAT", "AMT_INCOME_TOTAL"),
            ("AMT_GOODS_PRICE", "FLOAT", "AMT_GOODS_PRICE"),
            ("NAME_INCOME_TYPE", "VARCHAR", "NAME_INCOME_TYPE"),
            ("NAME_EDUCATION_TYPE", "VARCHAR", "NAME_EDUCATION_TYPE"),
            ("NAME_FAMILY_STATUS", "VARCHAR", "NAME_FAMILY_STATUS"),
            ("NAME_HOUSING_TYPE", "VARCHAR", "NAME_HOUSING_TYPE"),
            ("FLAG_OWN_CAR", "VARCHAR", "FLAG_OWN_CAR"),
            ("FLAG_OWN_REALTY", "VARCHAR", "FLAG_OWN_REALTY"),
            ("CNT_CHILDREN", "NUMBER", "CNT_CHILDREN"),
            ("OCCUPATION_TYPE", "VARCHAR", "OCCUPATION_TYPE"),
            ("ORGANIZATION_TYPE", "VARCHAR", "ORGANIZATION_TYPE"),
            ("REGION_RATING_CLIENT", "NUMBER", "REGION_RATING_CLIENT"),
            ("EXT_SOURCE_1", "FLOAT", "EXT_SOURCE_1"),
            ("EXT_SOURCE_2", "FLOAT", "EXT_SOURCE_2"),
            ("EXT_SOURCE_3", "FLOAT", "EXT_SOURCE_3"),
            ("DAYS_EMPLOYED_MASKED", "VARCHAR", "DAYS_EMPLOYED_MASKED"),
            ("DAYS_BIRTH_MASKED", "VARCHAR", "DAYS_BIRTH_MASKED"),
        ],
    },
    "SILVER_BUREAU": {
        "prefix": "silver_bureau",
        "expected_rows": 1_716_428,
        "columns": [
            ("SK_ID_CURR", "NUMBER", "SK_ID_CURR"),
            ("SK_ID_BUREAU", "NUMBER", "SK_ID_BUREAU"),
            ("CREDIT_ACTIVE", "VARCHAR", "CREDIT_ACTIVE"),
            ("CREDIT_CURRENCY", "VARCHAR", "CREDIT_CURRENCY"),
            ("DAYS_CREDIT", "NUMBER", "DAYS_CREDIT"),
            ("CREDIT_DAY_OVERDUE", "NUMBER", "CREDIT_DAY_OVERDUE"),
            ("DAYS_CREDIT_ENDDATE", "FLOAT", "DAYS_CREDIT_ENDDATE"),
            ("DAYS_CREDIT_UPDATE", "NUMBER", "DAYS_CREDIT_UPDATE"),
            ("AMT_CREDIT_SUM", "FLOAT", "AMT_CREDIT_SUM"),
            ("AMT_CREDIT_SUM_DEBT", "FLOAT", "AMT_CREDIT_SUM_DEBT"),
            ("AMT_CREDIT_SUM_LIMIT", "FLOAT", "AMT_CREDIT_SUM_LIMIT"),
            ("AMT_CREDIT_SUM_OVERDUE", "FLOAT", "AMT_CREDIT_SUM_OVERDUE"),
            ("CREDIT_TYPE", "VARCHAR", "CREDIT_TYPE"),
            ("CNT_CREDIT_PROLONG", "NUMBER", "CNT_CREDIT_PROLONG"),
        ],
    },
    "SILVER_BUREAU_BALANCE": {
        "prefix": "silver_bureau_balance",
        "expected_rows": 610_965,
        "columns": [
            ("SK_ID_BUREAU", "NUMBER", "SK_ID_BUREAU"),
            ("STATUS", "VARCHAR", "STATUS"),
        ],
    },
    "SILVER_INSTALLMENTS": {
        "prefix": "silver_installments",
        "expected_rows": 12_861_994,
        "columns": [
            ("SK_ID_PREV", "NUMBER", "SK_ID_PREV"),
            ("SK_ID_CURR", "NUMBER", "SK_ID_CURR"),
            ("NUM_INSTALMENT_VERSION", "FLOAT", "NUM_INSTALMENT_VERSION"),
            ("NUM_INSTALMENT_NUMBER", "FLOAT", "NUM_INSTALMENT_NUMBER"),
            ("DAYS_INSTALMENT", "FLOAT", "DAYS_INSTALMENT"),
            ("DAYS_ENTRY_PAYMENT", "FLOAT", "DAYS_ENTRY_PAYMENT"),
            ("AMT_INSTALMENT", "FLOAT", "AMT_INSTALMENT"),
            ("AMT_PAYMENT", "FLOAT", "AMT_PAYMENT"),
        ],
    },
}


def connect():
    load_dotenv(".env.dev")
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN"),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
    )


def ensure_stage(cur):
    cur.execute(f"""
        CREATE STAGE IF NOT EXISTS {STAGE_FQN}
        URL = '{STAGE_URL}'
        STORAGE_INTEGRATION = {STORAGE_INTEGRATION}
        FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT_FQN}')
    """)
    log.info(f"Stage ready: {STAGE_FQN} -> {STAGE_URL}")


def ensure_table(cur, table: str, spec: dict):
    cols_sql = ",\n    ".join(f"{col} {typ}" for col, typ, _ in spec["columns"])
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS HOME_CREDIT_RISK.STAGING.{table} (
            {cols_sql},
            INGESTION_TS VARCHAR,
            INGESTION_DATE VARCHAR
        )
    """)


def load_table(cur, table: str, spec: dict) -> int:
    select_cols = ",\n    ".join(
        f'$1:"{src}"::{typ} AS {col}' for col, typ, src in spec["columns"]
    )
    pattern = f"{spec['prefix']}/.*\\\\.parquet"
    copy_sql = f"""
        COPY INTO HOME_CREDIT_RISK.STAGING.{table}
        FROM (
            SELECT
                {select_cols},
                $1:"ingestion_ts"::VARCHAR AS INGESTION_TS,
                REGEXP_SUBSTR(METADATA$FILENAME, 'ingestion_date=([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})', 1, 1, 'e', 1)::VARCHAR AS INGESTION_DATE
            FROM @{STAGE_FQN}
            (PATTERN => '{pattern}')
        )
    """
    cur.execute(copy_sql)
    results = cur.fetchall()
    rows_loaded = sum(r[2] for r in results) if results else 0
    log.info(f"{table}: COPY INTO loaded {rows_loaded} rows from {len(results)} file(s)")

    cur.execute(f"SELECT COUNT(*) FROM HOME_CREDIT_RISK.STAGING.{table}")
    total = cur.fetchone()[0]
    expected = spec["expected_rows"]
    status = "OK" if total == expected else "MISMATCH"
    log.info(f"{table}: total rows = {total}, expected = {expected} [{status}]")
    return total


def main():
    conn = connect()
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS HOME_CREDIT_RISK.STAGING")
    ensure_stage(cur)
    for table, spec in TABLES.items():
        ensure_table(cur, table, spec)
    for table, spec in TABLES.items():
        load_table(cur, table, spec)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
