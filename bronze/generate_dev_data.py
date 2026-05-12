"""
Generate synthetic dev data for Phase 4a local testing.
Matches exact schema of all 7 Home Credit CSV files.
Use when Kaggle download unavailable (e.g., token expired / rules not accepted).

Output: data/application_train_dev_1000rows.csv + supporting files
"""

import random
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

N_APP = 1000
N_BUREAU = 1500
N_BB = 3000
N_PREV = 800
N_INSTALL = 2000
N_POS = 1500
N_CC = 600

SK_ID_CURR = list(range(100001, 100001 + N_APP))
SK_ID_BUREAU = list(range(200001, 200001 + N_BUREAU))
SK_ID_PREV = list(range(300001, 300001 + max(N_PREV, N_INSTALL, N_POS, N_CC)))


def _nullify(series, rate=0.1):
    mask = np.random.random(len(series)) < rate
    return series.where(~mask, other=None)


def make_application_train():
    contract_types = ["Cash loans", "Revolving loans"]
    income_types = ["Working", "Commercial associate", "Pensioner", "State servant", "Unemployed"]
    education_types = ["Secondary / secondary special", "Higher education", "Incomplete higher", "Lower secondary"]
    family_statuses = ["Married", "Single / not married", "Civil marriage", "Separated", "Widow"]
    housing_types = ["House / apartment", "Rented apartment", "With parents", "Municipal apartment"]
    org_types = ["Business Entity Type 3", "School", "Government", "Trade: type 7", "Medicine", "XNA"]
    occupation_types = ["Laborers", "Core staff", "Accountants", "Managers", "Drivers", None]

    days_employed = [random.choice([-random.randint(1, 5000), 365243]) for _ in range(N_APP)]

    df = pd.DataFrame({
        "SK_ID_CURR": SK_ID_CURR,
        "TARGET": np.random.choice([0, 1], N_APP, p=[0.92, 0.08]),
        "NAME_CONTRACT_TYPE": np.random.choice(contract_types, N_APP),
        "AMT_CREDIT": np.random.uniform(50000, 2000000, N_APP).round(2),
        "AMT_ANNUITY": np.random.uniform(5000, 100000, N_APP).round(2),
        "AMT_INCOME_TOTAL": np.random.uniform(50000, 500000, N_APP).round(2),
        "AMT_GOODS_PRICE": np.random.uniform(40000, 1800000, N_APP).round(2),
        "NAME_INCOME_TYPE": np.random.choice(income_types, N_APP),
        "NAME_EDUCATION_TYPE": np.random.choice(education_types, N_APP),
        "NAME_FAMILY_STATUS": np.random.choice(family_statuses, N_APP),
        "NAME_HOUSING_TYPE": np.random.choice(housing_types, N_APP),
        "DAYS_BIRTH": np.random.randint(-25000, -6000, N_APP),
        "DAYS_EMPLOYED": days_employed,
        "FLAG_OWN_CAR": np.random.choice(["Y", "N"], N_APP),
        "FLAG_OWN_REALTY": np.random.choice(["Y", "N"], N_APP),
        "CNT_CHILDREN": np.random.randint(0, 5, N_APP),
        "OCCUPATION_TYPE": [random.choice(occupation_types) for _ in range(N_APP)],
        "ORGANIZATION_TYPE": np.random.choice(org_types, N_APP),
        "REGION_RATING_CLIENT": np.random.choice([1, 2, 3], N_APP),
        "EXT_SOURCE_1": _nullify(pd.Series(np.random.uniform(0, 1, N_APP).round(6)), 0.3),
        "EXT_SOURCE_2": np.random.uniform(0, 1, N_APP).round(6),
        "EXT_SOURCE_3": _nullify(pd.Series(np.random.uniform(0, 1, N_APP).round(6)), 0.2),
    })
    return df


def make_bureau():
    credit_types = ["Consumer credit", "Credit card", "Car loan", "Mortgage", "Microloan"]
    credit_active = ["Active", "Closed", "Bad debt", "Sold"]
    df = pd.DataFrame({
        "SK_ID_CURR": np.random.choice(SK_ID_CURR, N_BUREAU),
        "SK_ID_BUREAU": SK_ID_BUREAU,
        "CREDIT_ACTIVE": np.random.choice(credit_active, N_BUREAU, p=[0.5, 0.4, 0.05, 0.05]),
        "CREDIT_CURRENCY": "currency 1",
        "DAYS_CREDIT": np.random.randint(-3000, 0, N_BUREAU),
        "CREDIT_DAY_OVERDUE": np.random.choice([0, 0, 0, 5, 30, 90], N_BUREAU),
        "DAYS_CREDIT_ENDDATE": _nullify(pd.Series(np.random.randint(-1000, 2000, N_BUREAU).astype(float)), 0.1),
        "DAYS_CREDIT_UPDATE": np.random.randint(-500, 0, N_BUREAU),
        "AMT_CREDIT_SUM": _nullify(pd.Series(np.random.uniform(10000, 1000000, N_BUREAU).round(2)), 0.05),
        "AMT_CREDIT_SUM_DEBT": _nullify(pd.Series(np.random.uniform(0, 500000, N_BUREAU).round(2)), 0.1),
        "AMT_CREDIT_SUM_LIMIT": _nullify(pd.Series(np.random.uniform(10000, 1000000, N_BUREAU).round(2)), 0.3),
        "AMT_CREDIT_SUM_OVERDUE": np.zeros(N_BUREAU),
        "CREDIT_TYPE": np.random.choice(credit_types, N_BUREAU),
        "CNT_CREDIT_PROLONG": np.random.choice([0, 1, 2], N_BUREAU, p=[0.85, 0.12, 0.03]),
    })
    return df


def make_bureau_balance():
    bb_rows = []
    statuses = ["C", "0", "1", "2", "3", "4", "5", "X"]
    for sk_id_bureau in SK_ID_BUREAU:
        months = random.randint(3, 12)
        for m in range(months):
            bb_rows.append({
                "SK_ID_BUREAU": sk_id_bureau,
                "MONTHS_BALANCE": -m,
                "STATUS": random.choice(statuses),
            })
    return pd.DataFrame(bb_rows)


def make_previous_application():
    contract_types = ["Cash loans", "Revolving loans", "Consumer loans"]
    statuses = ["Approved", "Refused", "Canceled", "Unused offer"]
    product_types = ["walk-in", "XNA", "x-sell"]
    df = pd.DataFrame({
        "SK_ID_PREV": SK_ID_PREV[:N_PREV],
        "SK_ID_CURR": np.random.choice(SK_ID_CURR, N_PREV),
        "NAME_CONTRACT_TYPE": np.random.choice(contract_types, N_PREV),
        "AMT_CREDIT": _nullify(pd.Series(np.random.uniform(10000, 1000000, N_PREV).round(2)), 0.05),
        "AMT_APPLICATION": np.random.uniform(10000, 1000000, N_PREV).round(2),
        "NAME_CONTRACT_STATUS": np.random.choice(statuses, N_PREV),
        "DAYS_DECISION": np.random.randint(-3000, 0, N_PREV),
        "NAME_PRODUCT_TYPE": np.random.choice(product_types, N_PREV),
    })
    return df


def make_installments():
    rows = []
    for sk_id_prev in SK_ID_PREV[:N_PREV]:
        sk_id_curr = random.choice(SK_ID_CURR)
        n_inst = random.randint(3, 24)
        for i in range(1, n_inst + 1):
            amt = round(random.uniform(1000, 50000), 2)
            days_inst = -random.randint(1, 2000)
            days_pay = days_inst + random.randint(-10, 30)
            rows.append({
                "SK_ID_PREV": sk_id_prev,
                "SK_ID_CURR": sk_id_curr,
                "NUM_INSTALMENT_VERSION": 1.0,
                "NUM_INSTALMENT_NUMBER": float(i),
                "DAYS_INSTALMENT": float(days_inst),
                "DAYS_ENTRY_PAYMENT": float(days_pay) if random.random() > 0.05 else None,
                "AMT_INSTALMENT": amt,
                "AMT_PAYMENT": amt if random.random() > 0.1 else None,
            })
    return pd.DataFrame(rows)


def make_pos_cash():
    rows = []
    statuses = ["Active", "Completed", "Returned to the store", "Demand", "Amortized debt"]
    for sk_id_prev in SK_ID_PREV[:N_PREV]:
        sk_id_curr = random.choice(SK_ID_CURR)
        months = random.randint(3, 12)
        cnt = random.randint(12, 60)
        for m in range(months):
            rows.append({
                "SK_ID_PREV": sk_id_prev,
                "SK_ID_CURR": sk_id_curr,
                "MONTHS_BALANCE": -m,
                "CNT_INSTALMENT": float(cnt),
                "CNT_INSTALMENT_FUTURE": float(max(0, cnt - m)),
                "NAME_CONTRACT_STATUS": random.choice(statuses),
                "SK_DPD": random.choice([0, 0, 0, 5, 30]),
                "SK_DPD_DEF": 0,
            })
    return pd.DataFrame(rows)


def make_credit_card():
    rows = []
    statuses = ["Active", "Completed", "Demand", "Signed"]
    for sk_id_prev in SK_ID_PREV[:N_CC]:
        sk_id_curr = random.choice(SK_ID_CURR)
        months = random.randint(2, 8)
        limit = round(random.uniform(10000, 200000), 2)
        for m in range(months):
            balance = round(random.uniform(0, limit), 2)
            rows.append({
                "SK_ID_PREV": sk_id_prev,
                "SK_ID_CURR": sk_id_curr,
                "MONTHS_BALANCE": -m,
                "AMT_BALANCE": balance,
                "AMT_CREDIT_LIMIT_ACTUAL": limit,
                "AMT_DRAWINGS_CURRENT": round(random.uniform(0, 5000), 2),
                "AMT_PAYMENT_CURRENT": round(random.uniform(0, 10000), 2),
                "SK_DPD": random.choice([0, 0, 0, 5]),
                "NAME_CONTRACT_STATUS": random.choice(statuses),
            })
    return pd.DataFrame(rows)


def main():
    print("Generating synthetic dev data...")

    app = make_application_train()
    app.to_csv(DATA_DIR / "application_train_dev_1000rows.csv", index=False)
    app.to_csv(DATA_DIR / "application_train.csv", index=False)
    print(f"  application_train: {len(app)} rows")

    bureau = make_bureau()
    bureau.to_csv(DATA_DIR / "bureau.csv", index=False)
    print(f"  bureau: {len(bureau)} rows")

    bb = make_bureau_balance()
    bb.to_csv(DATA_DIR / "bureau_balance.csv", index=False)
    print(f"  bureau_balance: {len(bb)} rows")

    prev = make_previous_application()
    prev.to_csv(DATA_DIR / "previous_application.csv", index=False)
    print(f"  previous_application: {len(prev)} rows")

    inst = make_installments()
    inst.to_csv(DATA_DIR / "installments_payments.csv", index=False)
    print(f"  installments_payments: {len(inst)} rows")

    pos = make_pos_cash()
    pos.to_csv(DATA_DIR / "POS_CASH_balance.csv", index=False)
    print(f"  POS_CASH_balance: {len(pos)} rows")

    cc = make_credit_card()
    cc.to_csv(DATA_DIR / "credit_card_balance.csv", index=False)
    print(f"  credit_card_balance: {len(cc)} rows")

    print("Done — synthetic dev data ready in data/")


if __name__ == "__main__":
    main()
