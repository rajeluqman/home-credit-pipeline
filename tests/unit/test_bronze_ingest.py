"""
Unit tests for bronze/ingest_bronze.py — dev mode (local parquet, no AWS).
"""

import sys
import shutil
import pandas as pd
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from bronze.ingest_bronze import ingest_dev


@pytest.fixture(autouse=True)
def cleanup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield
    # cleanup handled by tmp_path fixture


def _write_sample_csv(tmp_path: Path, filename: str, pk_col: str, rows: int = 5, nulls: int = 0):
    data = {pk_col: list(range(1, rows + 1 - nulls)) + [None] * nulls}
    data["AMT_CREDIT"] = [100000.0] * rows
    data["NAME_CONTRACT_TYPE"] = ["Cash loans"] * rows
    data["ingestion_ts"] = ["2026-05-12T00:00:00"] * rows
    data["ingestion_date"] = ["2026-05-12"] * rows
    (tmp_path / "data").mkdir(exist_ok=True)
    path = tmp_path / "data" / filename
    pd.DataFrame(data).to_csv(path, index=False)
    return path


def test_dev_ingest_application_clean(tmp_path):
    _write_sample_csv(tmp_path, "application_train_dev_1000rows.csv", "SK_ID_CURR", rows=5)
    result = ingest_dev("application_train", "2026-05-12")
    assert result["rows_written"] == 5
    assert result["quarantine_rows"] == 0


def test_dev_ingest_quarantines_null_pk(tmp_path):
    _write_sample_csv(tmp_path, "application_train_dev_1000rows.csv", "SK_ID_CURR", rows=5, nulls=2)
    result = ingest_dev("application_train", "2026-05-12")
    assert result["rows_written"] == 3
    assert result["quarantine_rows"] == 2


def test_dev_ingest_writes_parquet(tmp_path):
    _write_sample_csv(tmp_path, "application_train_dev_1000rows.csv", "SK_ID_CURR", rows=3)
    ingest_dev("application_train", "2026-05-12")
    out = tmp_path / "data" / "bronze" / "application_train" / "ingestion_date=2026-05-12" / "part-000.parquet"
    assert out.exists()


def test_dev_ingest_missing_file_returns_zero(tmp_path):
    (tmp_path / "data").mkdir(exist_ok=True)
    result = ingest_dev("bureau", "2026-05-12")
    assert result["rows_written"] == 0


def test_dev_ingest_adds_metadata_columns(tmp_path):
    _write_sample_csv(tmp_path, "application_train_dev_1000rows.csv", "SK_ID_CURR", rows=2)
    ingest_dev("application_train", "2026-05-12")
    out = tmp_path / "data" / "bronze" / "application_train" / "ingestion_date=2026-05-12" / "part-000.parquet"
    df = pd.read_parquet(out)
    assert "ingestion_ts" in df.columns
    assert "ingestion_date" in df.columns
