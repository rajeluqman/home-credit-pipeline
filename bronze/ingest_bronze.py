"""
Bronze ingestion — parameterised by --table and --env.

Dev  : reads local CSV → writes local parquet (data/bronze/{table}/)
Cloud: reads S3 landing → writes Delta on S3 (s3://{bucket}/bronze/{table}/)

PK nulls → quarantine path. Pipeline continues with clean rows.
"""

import os
import argparse
import hashlib
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ALL_TABLES = [
    "application_train",
    "bureau",
    "bureau_balance",
    "previous_application",
    "installments_payments",
    "POS_CASH_balance",
    "credit_card_balance",
]

PK_MAP = {
    "application_train": "SK_ID_CURR",
    "bureau": "SK_ID_BUREAU",
    "bureau_balance": "SK_ID_BUREAU",
    "previous_application": "SK_ID_PREV",
    "installments_payments": "SK_ID_PREV",
    "POS_CASH_balance": "SK_ID_PREV",
    "credit_card_balance": "SK_ID_PREV",
}

S3_SOURCE_FILENAME = {
    "application_train": "application_train.csv",
    "bureau": "bureau.csv",
    "bureau_balance": "bureau_balance.csv",
    "previous_application": "previous_application.csv",
    "installments_payments": "installments_payments.csv",
    "POS_CASH_balance": "POS_CASH_balance.csv",
    "credit_card_balance": "credit_card_balance.csv",
}


def load_env(env: str):
    env_file = f".env.{env}"
    if Path(env_file).exists():
        load_dotenv(env_file)
    log.info(f"env={env}")


def ingest_dev(table: str, ingestion_date: str) -> dict:
    """Read local dev sample CSV, add metadata cols, write local parquet."""
    if table == "application_train":
        source = Path("data") / "application_train_dev_1000rows.csv"
        if not source.exists():
            source = Path("data") / "application_train.csv"
    else:
        source = Path("data") / S3_SOURCE_FILENAME[table]

    if not source.exists():
        log.warning(f"Dev source not found: {source} — skipping {table}")
        return {"table": table, "rows_written": 0, "quarantine_rows": 0}

    df = pd.read_csv(source, low_memory=False)
    df["ingestion_ts"] = datetime.now(tz=None).isoformat()
    df["ingestion_date"] = ingestion_date

    pk = PK_MAP[table]
    quarantine = df[df[pk].isna()]
    clean = df[df[pk].notna()]

    out_dir = Path("data") / "bronze" / table / f"ingestion_date={ingestion_date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(out_dir / "part-000.parquet", index=False)

    if not quarantine.empty:
        q_dir = Path("data") / "quarantine" / "bronze" / table / f"ingestion_date={ingestion_date}"
        q_dir.mkdir(parents=True, exist_ok=True)
        quarantine.to_parquet(q_dir / "quarantine.parquet", index=False)
        log.warning(f"Quarantined {len(quarantine)} rows from {table} (NULL {pk})")

    log.info(f"[DEV] {table}: {len(clean)} rows → {out_dir}")
    return {"table": table, "rows_written": len(clean), "quarantine_rows": len(quarantine)}


def ingest_cloud(table: str, ingestion_date: str, env: str) -> dict:
    """Read S3 CSV → write Delta to S3. Requires delta-spark + pyspark."""
    import boto3
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from delta import configure_spark_with_delta_pip

    bucket = os.environ[f"S3_BUCKET_{env.upper()}"]
    region = os.getenv("AWS_REGION", "ap-southeast-1")
    filename = S3_SOURCE_FILENAME[table]
    s3_source = f"s3://{bucket}/landing/{filename}"
    s3_target = f"s3://{bucket}/bronze/{table}/ingestion_date={ingestion_date}/"
    s3_quarantine = f"s3://{bucket}/quarantine/bronze/{table}/ingestion_date={ingestion_date}/"
    pk = PK_MAP[table]

    builder = (
        SparkSession.builder.appName(f"bronze_ingest_{table}")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()

    df = spark.read.option("header", "true").option("inferSchema", "true").csv(s3_source)
    df = df.withColumn("ingestion_ts", F.current_timestamp()).withColumn("ingestion_date", F.lit(ingestion_date))

    quarantine = df.filter(F.col(pk).isNull())
    clean = df.filter(F.col(pk).isNotNull())

    q_count = quarantine.count()
    if q_count > 0:
        quarantine.write.mode("overwrite").parquet(s3_quarantine)
        log.warning(f"Quarantined {q_count} rows (NULL {pk})")

    clean.write.format("delta").mode("overwrite").save(s3_target)
    w_count = clean.count()
    log.info(f"[{env.upper()}] {table}: {w_count} rows → {s3_target}")
    return {"table": table, "rows_written": w_count, "quarantine_rows": q_count}


def run(table: str, env: str, ingestion_date: str = None) -> dict:
    ingestion_date = ingestion_date or date.today().isoformat()
    load_env(env)
    if env == "dev":
        return ingest_dev(table, ingestion_date)
    else:
        return ingest_cloud(table, ingestion_date, env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, choices=ALL_TABLES)
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"])
    parser.add_argument("--date", dest="ingestion_date", default=None,
                        help="ingestion_date override (YYYY-MM-DD)")
    args = parser.parse_args()

    result = run(args.table, args.env, args.ingestion_date)
    log.info(f"Done: {result}")


if __name__ == "__main__":
    main()
