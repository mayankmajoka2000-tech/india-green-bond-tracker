"""
India Green Bond & ESG Loan Tracker.

Command line:
    python tracker.py summary                 # totals by instrument, issuer type and year
    python tracker.py list --type "Green loan" --since 2025-01-01
    python tracker.py excel                   # rebuild output/India_Green_Finance_Tracker.xlsx

Data lives in data/deals.csv (one row per deal, amount in millions of the deal currency).
FX rates used to convert to USD and INR are set in FX below and in the workbook's FX sheet.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DEALS = ROOT / "data" / "deals.csv"

# Units of currency per 1 USD. Approximate October 2026 levels; edit to update.
FX = {"USD": 1.0, "INR": 88.0, "EUR": 0.86, "JPY": 150.0}

INSTRUMENTS = ["Green bond", "ESG bond", "Sustainability-linked bond",
               "Green loan", "Sustainability-linked loan"]
ISSUER_TYPES = ["Sovereign", "PSU NBFC", "Bank", "Corporate", "Municipal"]
STATUSES = ["Priced", "Signed", "Devolved", "Rejected", "Scheduled"]


def load() -> pd.DataFrame:
    df = pd.read_csv(DEALS, parse_dates=["date"])
    bad = df.loc[~df.currency.isin(FX), "deal_id"].tolist()
    if bad:
        raise ValueError(f"No FX rate for deals: {bad}")
    df["usd_mn"] = df.amount_mn / df.currency.map(FX)
    df["inr_crore"] = df.usd_mn * FX["INR"] / 10
    df["year"] = df.date.dt.year
    df["completed"] = df.status.isin(["Priced", "Signed", "Devolved"])
    return df


def summary(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    done = df[df.completed]
    agg = lambda g: done.groupby(g).agg(deals=("deal_id", "count"), usd_mn=("usd_mn", "sum")).round(0)
    return {"by_instrument": agg("instrument"), "by_issuer_type": agg("issuer_type"), "by_year": agg("year")}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("summary")
    ls = sub.add_parser("list")
    ls.add_argument("--type")
    ls.add_argument("--issuer-type")
    ls.add_argument("--since")
    sub.add_parser("excel")
    a = p.parse_args()

    df = load()
    if a.cmd == "summary":
        for name, t in summary(df).items():
            print(f"\n{name.replace('_', ' ').title()}\n{t.to_string()}")
        done = df[df.completed]
        print(f"\nCompleted deals: {len(done)}, total USD {done.usd_mn.sum():,.0f} mn "
              f"(Rs {done.inr_crore.sum():,.0f} crore)")
    elif a.cmd == "list":
        if a.type:
            df = df[df.instrument.str.lower() == a.type.lower()]
        if a.issuer_type:
            df = df[df.issuer_type.str.lower() == a.issuer_type.lower()]
        if a.since:
            df = df[df.date >= a.since]
        cols = ["date", "issuer", "instrument", "currency", "amount_mn", "usd_mn", "status"]
        print(df[cols].sort_values("date").to_string(index=False, float_format="{:,.0f}".format))
    elif a.cmd == "excel":
        from build_excel import build
        print(f"Saved {build(df)}")


if __name__ == "__main__":
    main()
