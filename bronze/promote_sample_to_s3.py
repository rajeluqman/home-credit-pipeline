"""
Phase-1 Gate-1 bridge — owner-approved one-time override (PROJECT_STATUS.md
"Active thread" 2026-06-30): the 5 Glue Silver jobs under glue/ are hardcoded to
`spark.read.format("delta").load(f"s3://{bucket}/bronze/{table}/ingestion_date={date}/")`
with no local/dev branch, while Bronze dev-mode (ingest_bronze.py::ingest_dev) writes
plain Parquet to a local path. To exercise the 5 Glue jobs UNCHANGED against the
local smart sample, this script bridges both directions over real S3 (Delta format):

  bronze-up   : data/bronze/{table}/ingestion_date={date}/part-000.parquet (local Parquet)
                -> local Delta table -> uploaded file-for-file to
                s3://{bucket}/bronze/{table}/ingestion_date={date}/ (Delta)
  silver-down : s3://{bucket}/silver/{silver_table}/ingestion_date={date}/ (Delta, written
                by the Glue job) -> downloaded locally -> coalesced to
                data/silver/{silver_table}/ingestion_date={date}/part-000.parquet (Parquet)
                so gx/run_silver_suite.py's unmodified dev-mode loader can validate it.

This is a Phase-1-only proof-run utility, not part of the regular Bronze/Silver/Gold
DAG chain. Phase 2 promotes the real ingest_cloud() path (S3 landing -> S3 Bronze
Delta directly); this bridge becomes dead code at that point.

Usage:
  python bronze/promote_sample_to_s3.py bronze-up   --date 2026-06-30 --bucket home-credit-risk-dev-1
  python bronze/promote_sample_to_s3.py silver-down --date 2026-06-30 --bucket home-credit-risk-dev-1
"""

import argparse
import logging
import shutil
from pathlib import Path

import boto3
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BRONZE_TABLES = [
    "application_train",
    "bureau",
    "bureau_balance",
    "previous_application",
    "installments_payments",
    "POS_CASH_balance",
    "credit_card_balance",
]

SILVER_TABLES = [
    "silver_application",
    "silver_bureau",
    "silver_bureau_balance",
    "silver_pos_cash",
    "silver_credit_card",
    "silver_installments",
    "silver_previous_application",
]


def _spark():
    from pyspark.sql import SparkSession
    from delta import configure_spark_with_delta_pip

    builder = (
        SparkSession.builder.appName("phase1_s3_bridge")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.driver.memory", "2g")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def _upload_dir(s3, local_dir: Path, bucket: str, s3_prefix: str):
    for path in local_dir.rglob("*"):
        if path.is_file():
            key = f"{s3_prefix}/{path.relative_to(local_dir).as_posix()}"
            s3.upload_file(str(path), bucket, key)


def _download_dir(s3, bucket: str, s3_prefix: str, local_dir: Path):
    paginator = s3.get_paginator("list_objects_v2")
    found = False
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{s3_prefix}/"):
        for obj in page.get("Contents", []):
            found = True
            rel = obj["Key"][len(s3_prefix) + 1:]
            dest = local_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, obj["Key"], str(dest))
    return found


def bronze_up(date: str, bucket: str, tables: list[str]):
    spark = _spark()
    s3 = boto3.client("s3")
    tmp_root = Path("data") / "_bridge_tmp" / "bronze_delta"
    results = {}

    for table in tables:
        src = Path("data") / "bronze" / table / f"ingestion_date={date}" / "part-000.parquet"
        if not src.exists():
            log.warning(f"Skip {table}: {src} not found")
            continue

        local_delta = tmp_root / table
        if local_delta.exists():
            shutil.rmtree(local_delta)

        df = spark.read.parquet(str(src))
        df.write.format("delta").mode("overwrite").save(str(local_delta))

        s3_prefix = f"bronze/{table}/ingestion_date={date}"
        _upload_dir(s3, local_delta, bucket, s3_prefix)
        row_count = df.count()
        results[table] = row_count
        log.info(f"bronze-up {table}: {row_count} rows -> s3://{bucket}/{s3_prefix}/")

    shutil.rmtree(tmp_root, ignore_errors=True)
    spark.stop()
    log.info(f"bronze-up complete: {results}")
    return results


def silver_down(date: str, bucket: str, silver_tables: list[str]):
    spark = _spark()
    s3 = boto3.client("s3")
    tmp_root = Path("data") / "_bridge_tmp" / "silver_delta"
    results = {}

    for silver_table in silver_tables:
        s3_prefix = f"silver/{silver_table}/ingestion_date={date}"
        local_delta = tmp_root / silver_table
        if local_delta.exists():
            shutil.rmtree(local_delta)

        found = _download_dir(s3, bucket, s3_prefix, local_delta)
        if not found:
            log.warning(f"Skip {silver_table}: s3://{bucket}/{s3_prefix}/ not found (job may not have run)")
            continue

        df = spark.read.format("delta").load(str(local_delta))
        out_dir = Path("data") / "silver" / silver_table / f"ingestion_date={date}"
        out_dir.mkdir(parents=True, exist_ok=True)

        pdf = df.toPandas()
        pdf.to_parquet(out_dir / "part-000.parquet", index=False)
        results[silver_table] = len(pdf)
        log.info(f"silver-down {silver_table}: {len(pdf)} rows -> {out_dir / 'part-000.parquet'}")

    shutil.rmtree(tmp_root, ignore_errors=True)
    spark.stop()
    log.info(f"silver-down complete: {results}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("direction", choices=["bronze-up", "silver-down"])
    parser.add_argument("--date", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--env", default="dev")
    args = parser.parse_args()

    env_file = f".env.{args.env}"
    if Path(env_file).exists():
        load_dotenv(env_file)

    if args.direction == "bronze-up":
        bronze_up(args.date, args.bucket, BRONZE_TABLES)
    else:
        silver_down(args.date, args.bucket, SILVER_TABLES)


if __name__ == "__main__":
    main()
