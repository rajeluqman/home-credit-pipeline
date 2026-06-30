"""
WHAT : Download Home Credit dataset dari Kaggle Competition API
WHY  : Competition format berbeza dari standard dataset — kena guna
       kaggle competitions download, BUKAN kaggle datasets download
WHEN : Run sekali sebelum pipeline start

CRITICAL: ini Kaggle COMPETITION, bukan standard dataset.
Command: kaggle competitions download -c home-credit-default-risk

Usage:
  python bronze/download_dataset.py --env dev
  python bronze/download_dataset.py --env staging
  python bronze/download_dataset.py --env prod
"""

import os
import argparse
import logging
import zipfile
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# WHAT: 7 source files untuk Home Credit pipeline
# WHY : Semua kena ingest untuk justify "7 disparate source tables" dalam resume
ALL_FILES = [
    "application_train.csv",
    "bureau.csv",
    "bureau_balance.csv",
    "previous_application.csv",
    "installments_payments.csv",
    "POS_CASH_balance.csv",
    "credit_card_balance.csv",
]

PRIMARY_FILE = "application_train.csv"


def load_env(env: str):
    """
    WHAT : Load .env file ikut environment
    WHY  : Setiap env ada credentials berbeza
    WHEN : First step sebelum any operation
    """
    env_file = f".env.{env}"
    if not Path(env_file).exists():
        raise FileNotFoundError(
            f"{env_file} tidak wujud.\n"
            f"Run: cp .env.example {env_file} dan fill in credentials."
        )
    load_dotenv(env_file)
    log.info(f"Loaded {env_file}")


def validate_kaggle_credentials():
    """
    WHAT : Validate Kaggle credentials
    WHY  : Fail fast sebelum API call
    WHEN : Sebelum download
    """
    token = os.getenv("KAGGLE_API_TOKEN")
    if not token:
        raise EnvironmentError(
            "KAGGLE_API_TOKEN mesti diset dalam .env.\n"
            "Setup: https://www.kaggle.com/settings/api → Create New Token"
        )
    os.environ["KAGGLE_API_TOKEN"] = token
    log.info("Kaggle credentials validated")


def download_competition_dataset(dest_dir: str = "data") -> str:
    """
    WHAT : Download Home Credit competition dataset dari Kaggle
    WHY  : Competition format — guna kaggle competitions download
           BUKAN kaggle datasets download (akan fail dengan 403)
    WHEN : Run sekali, skip kalau files dah ada
    Returns: path to data directory
    """
    import kaggle

    competition = os.getenv("KAGGLE_COMPETITION", "home-credit-default-risk")
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    # WHAT: Check kalau primary file dah ada — skip download
    primary_path = dest_path / PRIMARY_FILE
    if primary_path.exists():
        log.info(f"Dataset dah ada: {primary_path} — skip download")
        return str(dest_path)

    log.info(f"Downloading competition: {competition} → {dest_path}")
    log.info("⚠️  File besar — bureau_balance.csv = 27M rows. Ambil masa.")

    # WHAT: Download competition files
    # WHY : Competition API download dan auto-extract
    kaggle.api.competition_download_files(
        competition,
        path=str(dest_path),
        quiet=False
    )

    # WHAT: Unzip kalau perlu
    zip_path = dest_path / f"{competition}.zip"
    if zip_path.exists():
        log.info(f"Unzipping {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_path)
        zip_path.unlink()
        log.info("Unzip complete")

    # WHAT: Verify semua 7 files ada
    missing = [f for f in ALL_FILES if not (dest_path / f).exists()]
    if missing:
        log.warning(f"Files missing selepas download: {missing}")
    else:
        log.info(f"✅ Semua {len(ALL_FILES)} files verified")

    return str(dest_path)


def sample_dev_data(data_dir: str, rows: int = 1000) -> str:
    """
    WHAT : Sample N rows dari application_train untuk dev
    WHY  : 307k rows terlalu besar untuk dev — sample jimat memory dan DPU
    WHEN : Dev environment SAHAJA
    Returns: path to sampled CSV
    """
    import pandas as pd

    source = Path(data_dir) / PRIMARY_FILE
    sample_path = Path(data_dir) / f"application_train_dev_{rows}rows.csv"

    if sample_path.exists():
        log.info(f"Dev sample dah ada: {sample_path} — skip")
        return str(sample_path)

    log.info(f"Sampling {rows} rows dari {source}...")
    df = pd.read_csv(source, nrows=rows)
    df.to_csv(sample_path, index=False)
    log.info(f"Dev sample saved: {sample_path} ({len(df)} rows)")
    return str(sample_path)


def upload_all_to_s3(data_dir: str, env: str) -> dict:
    """
    WHAT : Upload semua 7 CSV ke S3 landing zone
    WHY  : S3 = single source of truth untuk staging/prod pipeline
    WHEN : Staging + prod environment
    Returns: dict of {filename: s3_path}
    """
    import boto3

    bucket = os.getenv(f"S3_BUCKET_{env.upper()}")
    region = os.getenv("AWS_REGION", "ap-southeast-1")

    if not bucket:
        raise EnvironmentError(f"S3_BUCKET_{env.upper()} tidak diset")

    s3 = boto3.client("s3", region_name=region)
    uploaded = {}

    for filename in ALL_FILES:
        local_path = Path(data_dir) / filename
        if not local_path.exists():
            log.warning(f"File tak jumpa — skip: {filename}")
            continue

        s3_key = f"landing/{filename}"
        s3_path = f"s3://{bucket}/{s3_key}"

        # WHAT: Skip kalau dah ada dengan size sama — jimat S3 PUT cost
        try:
            resp = s3.head_object(Bucket=bucket, Key=s3_key)
            if resp["ContentLength"] == local_path.stat().st_size:
                log.info(f"Skip (same size): {s3_path}")
                uploaded[filename] = s3_path
                continue
        except Exception:
            pass

        size_mb = local_path.stat().st_size / (1024 * 1024)
        log.info(f"Uploading {filename} ({size_mb:.1f} MB) → {s3_path}")
        s3.upload_file(str(local_path), bucket, s3_key)
        uploaded[filename] = s3_path
        log.info(f"✅ {filename} uploaded")

    return uploaded


def main():
    parser = argparse.ArgumentParser(
        description="Download Home Credit competition dataset dari Kaggle"
    )
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"])
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--keep-local", action="store_true",
                        help="Dev: keep local raw CSVs after S3 upload (default: delete — Flow B, "
                             "raw lives in S3 and scripts/smart_sample.py streams it from there).")
    args = parser.parse_args()

    log.info(f"=== Dataset Acquisition — env: {args.env} ===")

    load_env(args.env)
    validate_kaggle_credentials()

    data_dir = download_competition_dataset(dest_dir="data")

    if args.env == "dev":
        # Flow B (docs/ADDENDUM-A_local-dev-smart-sampling.md §2): land raw in the S3 dev bucket =
        # durable source-of-truth, then scripts/smart_sample.py STREAMS it from there. The 7 GB raw
        # need not persist on the ephemeral Codespace disk.
        dev_rows = args.rows or int(os.getenv("DEV_SAMPLE_ROWS", "1000"))
        sample_dev_data(data_dir, rows=dev_rows)  # naive head sample kept for the existing local-ingest path
        uploaded = upload_all_to_s3(data_dir, env="dev")
        landing = f"s3://{os.getenv('S3_BUCKET_DEV')}/landing"
        if not args.keep_local:
            for fname in ALL_FILES:
                (Path(data_dir) / fname).unlink(missing_ok=True)
            log.info("Removed local raw CSVs after upload (Flow B; pass --keep-local to retain)")
        log.info(f"=== Done — {len(uploaded)} raw files in {landing}/ ===")
        log.info(f"Next: python scripts/smart_sample.py --source-dir {landing} --out-dir data/sample")
    else:
        uploaded = upload_all_to_s3(data_dir, env=args.env)
        log.info(f"=== Done — {len(uploaded)} files uploaded ke S3 ===")
        for fname, path in uploaded.items():
            log.info(f"  {fname} → {path}")
        log.info(f"Set DATASET_SOURCE_PATH=s3://[bucket]/landing/ dalam .env.{args.env}")


if __name__ == "__main__":
    main()
