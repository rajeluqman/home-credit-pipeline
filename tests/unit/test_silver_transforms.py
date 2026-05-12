"""
Unit tests for silver/transforms.py — tests all transform functions with pandas.

Covers:
  - DI-001: ORGANIZATION_TYPE XNA → NULL
  - DI-002: DAYS_EMPLOYED 365243 → NULL before SHA-256
  - PII: DAYS_BIRTH and DAYS_EMPLOYED SHA-256 applied
  - PII: raw columns dropped from output
  - Dedup logic per table
  - bureau_balance MONTHS_BALANCE=0 filter
"""

import hashlib
import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from silver.transforms import (
    transform_application,
    transform_bureau,
    transform_bureau_balance,
    transform_previous_application,
    transform_installments,
    transform_pos_cash,
    transform_credit_card,
)


def _sha256(val) -> str:
    return hashlib.sha256(str(val).encode()).hexdigest()


def _make_app_df(**overrides) -> pd.DataFrame:
    base = {
        "SK_ID_CURR": [100001, 100002],
        "TARGET": [0, 1],
        "NAME_CONTRACT_TYPE": ["Cash loans", "Revolving loans"],
        "AMT_CREDIT": [500000.0, 250000.0],
        "AMT_ANNUITY": [25000.0, 10000.0],
        "AMT_INCOME_TOTAL": [100000.0, 80000.0],
        "AMT_GOODS_PRICE": [450000.0, 230000.0],
        "NAME_INCOME_TYPE": ["Working", "Commercial associate"],
        "NAME_EDUCATION_TYPE": ["Secondary", "Higher education"],
        "NAME_FAMILY_STATUS": ["Married", "Single"],
        "NAME_HOUSING_TYPE": ["House / apartment", "Rented apartment"],
        "DAYS_BIRTH": [-12000, -15000],
        "DAYS_EMPLOYED": [-3000, 365243],
        "FLAG_OWN_CAR": ["Y", "N"],
        "FLAG_OWN_REALTY": ["Y", "Y"],
        "CNT_CHILDREN": [0, 1],
        "OCCUPATION_TYPE": ["Laborers", None],
        "ORGANIZATION_TYPE": ["Business Entity Type 3", "XNA"],
        "REGION_RATING_CLIENT": [2, 1],
        "EXT_SOURCE_1": [0.5, 0.3],
        "EXT_SOURCE_2": [0.6, 0.4],
        "EXT_SOURCE_3": [0.7, None],
        "ingestion_ts": ["2026-05-12T00:00:00", "2026-05-12T00:00:00"],
        "ingestion_date": ["2026-05-12", "2026-05-12"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestTransformApplication:
    def test_xna_becomes_null(self):
        df = _make_app_df()
        out = transform_application(df)
        assert out["ORGANIZATION_TYPE"].isna().any(), "XNA should become NULL"
        assert "XNA" not in out["ORGANIZATION_TYPE"].dropna().values

    def test_days_employed_365243_masked_as_null(self):
        df = _make_app_df()
        out = transform_application(df)
        # Row with DAYS_EMPLOYED=365243 → DAYS_EMPLOYED_MASKED should be NULL
        row = out[out["SK_ID_CURR"] == 100002]
        assert pd.isna(row["DAYS_EMPLOYED_MASKED"].values[0]), "365243 should yield NULL masked value"

    def test_days_employed_non_365243_is_masked(self):
        df = _make_app_df()
        out = transform_application(df)
        row = out[out["SK_ID_CURR"] == 100001]
        expected = _sha256(-3000)
        assert row["DAYS_EMPLOYED_MASKED"].values[0] == expected

    def test_days_birth_always_masked(self):
        df = _make_app_df()
        out = transform_application(df)
        for _, row in out.iterrows():
            assert pd.notna(row["DAYS_BIRTH_MASKED"]), "DAYS_BIRTH_MASKED must never be null"
            assert len(row["DAYS_BIRTH_MASKED"]) == 64, "SHA-256 hex must be 64 chars"

    def test_raw_pii_columns_dropped(self):
        df = _make_app_df()
        out = transform_application(df)
        assert "DAYS_BIRTH" not in out.columns
        assert "DAYS_EMPLOYED" not in out.columns
        assert "DAYS_EMPLOYED_CLEAN" not in out.columns

    def test_dedup_keeps_latest(self):
        df = pd.concat([_make_app_df()] * 2).reset_index(drop=True)
        df.loc[2, "ingestion_ts"] = "2026-05-13T00:00:00"  # newer duplicate of row 0
        df.loc[3, "ingestion_ts"] = "2026-05-13T00:00:00"
        out = transform_application(df)
        assert out["SK_ID_CURR"].duplicated().sum() == 0
        assert len(out) == 2

    def test_output_has_no_days_birth_in_plain(self):
        df = _make_app_df()
        out = transform_application(df)
        # Masked value must differ from original plain string
        raw_val = str(-12000)
        assert out["DAYS_BIRTH_MASKED"].values[0] != raw_val


class TestTransformBureau:
    def _make_bureau_df(self):
        return pd.DataFrame({
            "SK_ID_CURR": [100001, 100001, 100002],
            "SK_ID_BUREAU": [200001, 200001, 200002],
            "CREDIT_ACTIVE": ["Active", "Active", "Closed"],
            "CREDIT_CURRENCY": ["currency 1"] * 3,
            "DAYS_CREDIT": [-500, -500, -200],
            "CREDIT_DAY_OVERDUE": [0, 0, 5],
            "DAYS_CREDIT_ENDDATE": [100.0, 100.0, 50.0],
            "DAYS_CREDIT_UPDATE": [-10, -10, -5],
            "AMT_CREDIT_SUM": [100000.0, 100000.0, 50000.0],
            "AMT_CREDIT_SUM_DEBT": [50000.0, 50000.0, 0.0],
            "AMT_CREDIT_SUM_LIMIT": [100000.0, 100000.0, 50000.0],
            "AMT_CREDIT_SUM_OVERDUE": [0.0, 0.0, 0.0],
            "CREDIT_TYPE": ["Consumer credit"] * 3,
            "CNT_CREDIT_PROLONG": [0, 0, 1],
            "ingestion_ts": ["2026-05-12T01:00:00", "2026-05-12T00:00:00", "2026-05-12T00:00:00"],
            "ingestion_date": ["2026-05-12"] * 3,
        })

    def test_dedup_on_sk_id_bureau(self):
        df = self._make_bureau_df()
        out = transform_bureau(df)
        assert out["SK_ID_BUREAU"].duplicated().sum() == 0

    def test_keeps_latest_ingestion_ts(self):
        df = self._make_bureau_df()
        out = transform_bureau(df)
        row = out[out["SK_ID_BUREAU"] == 200001]
        assert row["ingestion_ts"].values[0] == "2026-05-12T01:00:00"


class TestTransformBureauBalance:
    def _make_bb_df(self):
        return pd.DataFrame({
            "SK_ID_BUREAU": [200001, 200001, 200001, 200002],
            "MONTHS_BALANCE": [0, -1, -2, 0],
            "STATUS": ["C", "0", "X", "1"],
            "ingestion_ts": ["2026-05-12T00:00:00"] * 4,
            "ingestion_date": ["2026-05-12"] * 4,
        })

    def test_filters_months_balance_zero(self):
        df = self._make_bb_df()
        out = transform_bureau_balance(df)
        assert len(out) == 2  # 1 per SK_ID_BUREAU

    def test_one_row_per_bureau(self):
        df = self._make_bb_df()
        out = transform_bureau_balance(df)
        assert out["SK_ID_BUREAU"].duplicated().sum() == 0

    def test_status_at_months_zero(self):
        df = self._make_bb_df()
        out = transform_bureau_balance(df)
        row = out[out["SK_ID_BUREAU"] == 200001]
        assert row["STATUS"].values[0] == "C"


class TestTransformPreviousApplication:
    def test_column_subset(self):
        df = pd.DataFrame({
            "SK_ID_PREV": [300001],
            "SK_ID_CURR": [100001],
            "NAME_CONTRACT_TYPE": ["Cash loans"],
            "AMT_CREDIT": [100000.0],
            "AMT_APPLICATION": [100000.0],
            "NAME_CONTRACT_STATUS": ["Approved"],
            "DAYS_DECISION": [-500],
            "NAME_PRODUCT_TYPE": ["walk-in"],
            "EXTRA_COLUMN": ["drop me"],
            "ingestion_ts": ["2026-05-12T00:00:00"],
            "ingestion_date": ["2026-05-12"],
        })
        out = transform_previous_application(df)
        assert "EXTRA_COLUMN" not in out.columns
        assert "SK_ID_PREV" in out.columns


class TestTransformInstallments:
    def _make_install_df(self):
        return pd.DataFrame({
            "SK_ID_PREV": [300001, 300001, 300002],
            "SK_ID_CURR": [100001, 100001, 100002],
            "NUM_INSTALMENT_VERSION": [1.0, 1.0, 1.0],
            "NUM_INSTALMENT_NUMBER": [1.0, 1.0, 2.0],
            "DAYS_INSTALMENT": [-100.0, -100.0, -50.0],
            "DAYS_ENTRY_PAYMENT": [-95.0, -95.0, -48.0],
            "AMT_INSTALMENT": [5000.0, 5000.0, 3000.0],
            "AMT_PAYMENT": [5000.0, 5000.0, 3000.0],
            "ingestion_ts": ["2026-05-12T01:00:00", "2026-05-12T00:00:00", "2026-05-12T00:00:00"],
            "ingestion_date": ["2026-05-12"] * 3,
        })

    def test_dedup_on_composite_key(self):
        df = self._make_install_df()
        out = transform_installments(df)
        dupes = out.duplicated(subset=["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"]).sum()
        assert dupes == 0

    def test_keeps_latest_for_duplicate_key(self):
        df = self._make_install_df()
        out = transform_installments(df)
        row = out[(out["SK_ID_PREV"] == 300001) & (out["NUM_INSTALMENT_NUMBER"] == 1.0)]
        assert row["ingestion_ts"].values[0] == "2026-05-12T01:00:00"


class TestTransformPosCash:
    def test_column_subset(self):
        df = pd.DataFrame({
            "SK_ID_PREV": [400001],
            "SK_ID_CURR": [100001],
            "MONTHS_BALANCE": [-1],
            "CNT_INSTALMENT": [12.0],
            "CNT_INSTALMENT_FUTURE": [6.0],
            "NAME_CONTRACT_STATUS": ["Active"],
            "SK_DPD": [0],
            "SK_DPD_DEF": [0],
            "IRRELEVANT_COL": ["x"],
            "ingestion_ts": ["2026-05-12T00:00:00"],
            "ingestion_date": ["2026-05-12"],
        })
        out = transform_pos_cash(df)
        assert "IRRELEVANT_COL" not in out.columns
        assert "SK_DPD" in out.columns


class TestTransformCreditCard:
    def test_column_subset(self):
        df = pd.DataFrame({
            "SK_ID_PREV": [500001],
            "SK_ID_CURR": [100001],
            "MONTHS_BALANCE": [-1],
            "AMT_BALANCE": [10000.0],
            "AMT_CREDIT_LIMIT_ACTUAL": [20000],
            "AMT_DRAWINGS_CURRENT": [500.0],
            "AMT_PAYMENT_CURRENT": [1000.0],
            "SK_DPD": [0],
            "NAME_CONTRACT_STATUS": ["Active"],
            "EXTRA": ["drop"],
            "ingestion_ts": ["2026-05-12T00:00:00"],
            "ingestion_date": ["2026-05-12"],
        })
        out = transform_credit_card(df)
        assert "EXTRA" not in out.columns
        assert "AMT_BALANCE" in out.columns
