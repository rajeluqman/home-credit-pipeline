"""
Pandas-based Silver transforms — mirrors the PySpark logic in glue/.
Used for: local dev testing + unit tests.

Each function takes a raw DataFrame (Bronze-equivalent) and returns clean Silver DataFrame.
Column names and transform order match PIPELINE_SPEC exactly.
"""

import hashlib
import pandas as pd


def _sha256(value) -> str | None:
    if pd.isna(value):
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()


# ── Application ──────────────────────────────────────────────────────────────

APPLICATION_COLS = [
    "SK_ID_CURR", "TARGET", "NAME_CONTRACT_TYPE", "AMT_CREDIT", "AMT_ANNUITY",
    "AMT_INCOME_TOTAL", "AMT_GOODS_PRICE", "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE", "DAYS_BIRTH", "DAYS_EMPLOYED",
    "FLAG_OWN_CAR", "FLAG_OWN_REALTY", "CNT_CHILDREN", "OCCUPATION_TYPE",
    "ORGANIZATION_TYPE", "REGION_RATING_CLIENT", "EXT_SOURCE_1", "EXT_SOURCE_2",
    "EXT_SOURCE_3", "ingestion_ts", "ingestion_date",
]


def transform_application(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in APPLICATION_COLS if c in df.columns]
    out = df[existing].copy()

    # DI-001: XNA → NULL
    out["ORGANIZATION_TYPE"] = out["ORGANIZATION_TYPE"].replace("XNA", None)

    # DI-002: 365243 → NULL (before PII mask)
    out["DAYS_EMPLOYED_CLEAN"] = out["DAYS_EMPLOYED"].where(out["DAYS_EMPLOYED"] != 365243, other=None)

    # PII: SHA-256 — cast to int before str() to avoid "-3000.0" float repr
    out["DAYS_EMPLOYED_MASKED"] = out["DAYS_EMPLOYED_CLEAN"].apply(
        lambda x: _sha256(int(x)) if pd.notna(x) else None
    )
    out["DAYS_BIRTH_MASKED"] = out["DAYS_BIRTH"].apply(
        lambda x: _sha256(int(x)) if pd.notna(x) else None
    )

    # Drop raw PII
    out = out.drop(columns=["DAYS_BIRTH", "DAYS_EMPLOYED", "DAYS_EMPLOYED_CLEAN"], errors="ignore")

    # Dedup: keep latest per SK_ID_CURR
    out = (
        out.sort_values("ingestion_ts", ascending=False)
        .drop_duplicates(subset=["SK_ID_CURR"], keep="first")
        .reset_index(drop=True)
    )
    return out


# ── Bureau ────────────────────────────────────────────────────────────────────

BUREAU_COLS = [
    "SK_ID_CURR", "SK_ID_BUREAU", "CREDIT_ACTIVE", "CREDIT_CURRENCY",
    "DAYS_CREDIT", "CREDIT_DAY_OVERDUE", "DAYS_CREDIT_ENDDATE",
    "DAYS_CREDIT_UPDATE", "AMT_CREDIT_SUM", "AMT_CREDIT_SUM_DEBT",
    "AMT_CREDIT_SUM_LIMIT", "AMT_CREDIT_SUM_OVERDUE", "CREDIT_TYPE",
    "CNT_CREDIT_PROLONG", "ingestion_ts", "ingestion_date",
]


def transform_bureau(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in BUREAU_COLS if c in df.columns]
    out = df[existing].copy()
    out = (
        out.sort_values("ingestion_ts", ascending=False)
        .drop_duplicates(subset=["SK_ID_BUREAU"], keep="first")
        .reset_index(drop=True)
    )
    return out


# ── Bureau Balance ────────────────────────────────────────────────────────────

def transform_bureau_balance(df: pd.DataFrame) -> pd.DataFrame:
    # Filter to most recent month per bureau record
    recent = df[df["MONTHS_BALANCE"] == 0].copy()

    # 1 row per SK_ID_BUREAU (STATUS at MONTHS_BALANCE=0)
    out = (
        recent[["SK_ID_BUREAU", "STATUS", "ingestion_ts", "ingestion_date"]]
        .drop_duplicates(subset=["SK_ID_BUREAU"], keep="first")
        .reset_index(drop=True)
    )
    return out


# ── Previous Application ──────────────────────────────────────────────────────

PREV_APP_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "NAME_CONTRACT_TYPE", "AMT_CREDIT",
    "AMT_APPLICATION", "NAME_CONTRACT_STATUS", "DAYS_DECISION",
    "NAME_PRODUCT_TYPE", "ingestion_ts", "ingestion_date",
]


def transform_previous_application(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in PREV_APP_COLS if c in df.columns]
    return df[existing].copy().reset_index(drop=True)


# ── Installments ──────────────────────────────────────────────────────────────

INSTALLMENTS_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "NUM_INSTALMENT_VERSION", "NUM_INSTALMENT_NUMBER",
    "DAYS_INSTALMENT", "DAYS_ENTRY_PAYMENT", "AMT_INSTALMENT", "AMT_PAYMENT",
    "ingestion_ts", "ingestion_date",
]


def transform_installments(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in INSTALLMENTS_COLS if c in df.columns]
    out = df[existing].copy()
    # Dedup on composite key — keep latest
    out = (
        out.sort_values("ingestion_ts", ascending=False)
        .drop_duplicates(subset=["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"], keep="first")
        .reset_index(drop=True)
    )
    return out


# ── POS Cash Balance ──────────────────────────────────────────────────────────

POS_CASH_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "MONTHS_BALANCE", "CNT_INSTALMENT",
    "CNT_INSTALMENT_FUTURE", "NAME_CONTRACT_STATUS", "SK_DPD", "SK_DPD_DEF",
    "ingestion_ts", "ingestion_date",
]


def transform_pos_cash(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in POS_CASH_COLS if c in df.columns]
    return df[existing].copy().reset_index(drop=True)


# ── Credit Card Balance ───────────────────────────────────────────────────────

CREDIT_CARD_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "MONTHS_BALANCE", "AMT_BALANCE",
    "AMT_CREDIT_LIMIT_ACTUAL", "AMT_DRAWINGS_CURRENT", "AMT_PAYMENT_CURRENT",
    "SK_DPD", "NAME_CONTRACT_STATUS", "ingestion_ts", "ingestion_date",
]


def transform_credit_card(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in CREDIT_CARD_COLS if c in df.columns]
    return df[existing].copy().reset_index(drop=True)
