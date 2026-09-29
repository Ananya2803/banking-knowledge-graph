"""Download the Berka (PKDD'99) Czech bank dataset and save it as clean English CSVs.

The original files use Czech codes and packed dates (e.g. 930705 = 1993-07-05).
This script translates them once, so the rest of the project reads plain CSVs.
"""

import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

DATA_URL = "https://web.archive.org/web/20070214120527id_/http://lisp.vse.cz/pkdd99/DATA/data_berka.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FREQUENCY = {
    "POPLATEK MESICNE": "monthly",
    "POPLATEK TYDNE": "weekly",
    "POPLATEK PO OBRATU": "after_transaction",
}
LOAN_STATUS = {
    "A": "finished_ok",
    "B": "finished_unpaid",
    "C": "running_ok",
    "D": "running_in_debt",
}
PAYMENT_PURPOSE = {
    "POJISTNE": "insurance",
    "SIPO": "household",
    "LEASING": "leasing",
    "UVER": "loan_repayment",
}
HOLDER_ROLE = {"OWNER": "owner", "DISPONENT": "authorised_user"}


def to_date(packed):
    """930705 or '931107 00:00:00' -> '1993-07-05'."""
    s = str(packed)[:6]
    return f"19{s[:2]}-{s[2:4]}-{s[4:6]}"


def read(zf, name):
    return pd.read_csv(io.BytesIO(zf.read(name)), sep=";", low_memory=False)


def clean(zf):
    clients = read(zf, "client.asc")
    # birth_number is YYMMDD; for women 50 is added to the month.
    bn = clients["birth_number"].astype(str).str.zfill(6)
    month = bn.str[2:4].astype(int)
    clients["gender"] = month.gt(50).map({True: "F", False: "M"})
    clients["birth_year"] = 1900 + bn.str[:2].astype(int)
    clients = clients[["client_id", "gender", "birth_year", "district_id"]]

    accounts = read(zf, "account.asc")
    accounts["statement_frequency"] = accounts["frequency"].map(FREQUENCY)
    accounts["opened"] = accounts["date"].map(to_date)
    accounts = accounts[["account_id", "district_id", "statement_frequency", "opened"]]

    holders = read(zf, "disp.asc")
    holders["role"] = holders["type"].map(HOLDER_ROLE)
    holders = holders[["disp_id", "client_id", "account_id", "role"]]

    loans = read(zf, "loan.asc")
    loans["status"] = loans["status"].map(LOAN_STATUS)
    loans["defaulted"] = loans["status"].isin(["finished_unpaid", "running_in_debt"])
    loans["date"] = loans["date"].map(to_date)
    loans = loans.rename(columns={"duration": "duration_months", "payments": "monthly_payment"})

    cards = read(zf, "card.asc")
    cards["issued"] = cards["issued"].map(to_date)
    cards = cards.rename(columns={"type": "card_type"})

    orders = read(zf, "order.asc")
    orders["purpose"] = orders["k_symbol"].str.strip().map(PAYMENT_PURPOSE).fillna("other")
    orders = orders[["order_id", "account_id", "bank_to", "amount", "purpose"]]

    districts = read(zf, "district.asc")
    districts = districts.rename(columns={
        "A1": "district_id", "A2": "name", "A3": "region", "A4": "inhabitants",
        "A11": "avg_salary", "A13": "unemployment_rate", "A16": "crimes",
    })[["district_id", "name", "region", "inhabitants", "avg_salary", "unemployment_rate", "crimes"]]

    return {
        "clients": clients,
        "accounts": accounts,
        "account_holders": holders,
        "loans": loans,
        "cards": cards,
        "payment_orders": orders,
        "districts": districts,
    }


def main():
    print(f"Downloading {DATA_URL} ...")
    with urlopen(DATA_URL, timeout=120) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
    DATA_DIR.mkdir(exist_ok=True)
    for name, df in clean(zf).items():
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)
        print(f"  data/{name}.csv  ({len(df):,} rows)")


if __name__ == "__main__":
    main()
