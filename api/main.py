"""
India Green Finance API.

Deal-level data on labelled green, ESG and sustainability-linked bonds and loans raised by Indian
issuers (Jan 2023 - Oct 2026), plus sovereign green bond auction outcomes and greenium.
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from tracker import FX, INSTRUMENTS, ISSUER_TYPES, STATUSES, load

ROOT = Path(__file__).resolve().parents[1]
DEALS = load()
SOV = pd.read_csv(ROOT / "data" / "sovereign_auctions.csv")
VERSION = "1.0.0"

app = FastAPI(
    title="India Green Finance API",
    version=VERSION,
    description=(
        "Green bonds, ESG bonds, green loans and sustainability-linked loans raised by Indian issuers, "
        "January 2023 to October 2026, with sovereign green bond auction results and greenium. "
        "Every deal links to its public source. Amounts are converted to USD and INR crore at fixed "
        "FX rates (see /fx). A curated sample, not a complete market database."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

Instrument = Literal[tuple(INSTRUMENTS)]
IssuerType = Literal[tuple(ISSUER_TYPES)]
Status = Literal[tuple(STATUSES)]


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    if hasattr(v, "item"):
        v = v.item()
    return round(v, 2) if isinstance(v, float) else v


def _deal(row: pd.Series) -> dict:
    d = {k: _clean(v) for k, v in row.items()}
    return {
        "deal_id": d["deal_id"], "date": d["date"], "issuer": d["issuer"],
        "issuer_type": d["issuer_type"], "sector": d["sector"],
        "instrument": d["instrument"], "green_label": d["green_label"],
        "amount": {"currency": d["currency"], "millions": d["amount_mn"],
                   "usd_mn": d["usd_mn"], "inr_crore": d["inr_crore"]},
        "tenor_years": d["tenor_years"], "pricing": d["pricing"],
        "lenders_investors": d["lenders_investors"],
        "use_of_proceeds_or_kpis": d["use_of_proceeds_or_kpis"],
        "status": d["status"], "counted_in_totals": d["completed"],
        "source_url": d["source_url"],
    }


def _filter(df, instrument=None, issuer_type=None, status=None, year=None,
            since=None, until=None, issuer=None, min_usd_mn=None, completed_only=False):
    if instrument:
        df = df[df.instrument == instrument]
    if issuer_type:
        df = df[df.issuer_type == issuer_type]
    if status:
        df = df[df.status == status]
    if year:
        df = df[df.year == year]
    if since:
        df = df[df.date >= pd.Timestamp(since)]
    if until:
        df = df[df.date <= pd.Timestamp(until)]
    if issuer:
        df = df[df.issuer.str.contains(issuer, case=False, regex=False)]
    if min_usd_mn is not None:
        df = df[df.usd_mn >= min_usd_mn]
    if completed_only:
        df = df[df.completed]
    return df


def _group(df, col):
    g = (df.groupby(col).agg(deals=("deal_id", "count"), usd_mn=("usd_mn", "sum"))
         .sort_values("usd_mn", ascending=False))
    total = df.usd_mn.sum()
    return [{"key": _clean(k), "deals": int(r.deals), "usd_mn": round(float(r.usd_mn), 1),
             "share": round(float(r.usd_mn / total), 4) if total else None}
            for k, r in g.iterrows()]


# ------------------------------------------------------------------------ routes
@app.get("/", tags=["System"])
def root():
    done = DEALS[DEALS.completed]
    return {
        "name": "India Green Finance API", "version": VERSION, "status": "operational", "docs": "/docs",
        "coverage": {"from": DEALS.date.min().date().isoformat(), "to": DEALS.date.max().date().isoformat(),
                     "deals": len(DEALS), "completed_deals": len(done),
                     "completed_usd_mn": round(float(done.usd_mn.sum()), 1)},
        "endpoints": ["/deals", "/deals/{deal_id}", "/summary", "/issuers",
                      "/sovereign/auctions", "/sovereign/greenium", "/sll/kpis", "/fx"],
    }


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "version": VERSION}


@app.get("/deals", tags=["Deals"], summary="Search and filter deals")
def deals(instrument: Instrument | None = None,
          issuer_type: IssuerType | None = None,
          status: Status | None = None,
          year: int | None = Query(None, ge=2023, le=2030),
          since: date | None = None, until: date | None = None,
          issuer: str | None = Query(None, description="Case-insensitive substring, e.g. 'tata'"),
          min_usd_mn: float | None = Query(None, ge=0),
          sort: Literal["date", "usd_mn"] = "date",
          limit: int = Query(100, ge=1, le=500)):
    df = _filter(DEALS, instrument, issuer_type, status, year, since, until, issuer, min_usd_mn)
    df = df.sort_values(sort, ascending=(sort == "date"), na_position="last")
    return {"count": len(df), "deals": [_deal(r) for _, r in df.head(limit).iterrows()]}


@app.get("/deals/{deal_id}", tags=["Deals"], summary="One deal by ID")
def deal(deal_id: str):
    m = DEALS[DEALS.deal_id.str.upper() == deal_id.upper()]
    if m.empty:
        raise HTTPException(404, f"No deal '{deal_id}'. List IDs via GET /deals")
    return _deal(m.iloc[0])


@app.get("/summary", tags=["Analytics"], summary="Totals by instrument, issuer type and year")
def summary(since: date | None = None, until: date | None = None):
    df = _filter(DEALS, since=since, until=until, completed_only=True)
    total = float(df.usd_mn.sum())
    return {
        "basis": "Completed deals (Priced, Signed, Devolved); USD mn at /fx rates",
        "completed_deals": len(df), "total_usd_mn": round(total, 1),
        "total_inr_crore": round(total * FX["INR"] / 10, 0),
        "largest_deal": _deal(df.loc[df.usd_mn.idxmax()]) if len(df) else None,
        "by_instrument": _group(df, "instrument"),
        "by_issuer_type": _group(df, "issuer_type"),
        "by_year": _group(df, "year"),
    }


@app.get("/issuers", tags=["Analytics"], summary="Issuers ranked by green / ESG debt raised")
def issuers(issuer_type: IssuerType | None = None):
    df = _filter(DEALS, issuer_type=issuer_type, completed_only=True)
    rows = []
    for name, g in df.groupby("issuer"):
        rows.append({"issuer": name, "issuer_type": g.issuer_type.iloc[0], "deals": len(g),
                     "usd_mn": round(float(g.usd_mn.sum()), 1),
                     "instruments": sorted(g.instrument.unique().tolist()),
                     "latest": g.date.max().date().isoformat()})
    rows.sort(key=lambda r: -r["usd_mn"])
    return {"count": len(rows), "issuers": rows}


@app.get("/sovereign/auctions", tags=["Sovereign"], summary="Every sovereign green bond auction outcome")
def sovereign_auctions():
    rows = [{k: _clean(v) for k, v in r.items()} for _, r in SOV.iterrows()]
    return {"count": len(rows), "auctions": rows,
            "outstanding_inr_bn_aug_2026": 877,
            "outstanding_source": "https://www.brecorder.com/news/amp/40434824"}


@app.get("/sovereign/greenium", tags=["Sovereign"], summary="Greenium history and what it means")
def sovereign_greenium():
    g = SOV.dropna(subset=["greenium_bps"])
    failed = SOV[SOV.outcome.str.contains("Cancelled|devolved|rejected", case=False)]
    return {
        "definition": "Yield discount of a green bond vs a comparable conventional G-sec, in basis points",
        "observations": [{"auction": r.auction, "tenor": _clean(r.tenor), "greenium_bps": int(r.greenium_bps)}
                         for r in g.itertuples()],
        "average_bps": round(float(g.greenium_bps.mean()), 2),
        "weak_auctions": [{"auction": r.auction, "outcome": r.outcome} for r in failed.itertuples()],
        "takeaway": ("Demand for 5- and 10-year green G-secs was weak in 2024-25 (cancelled, devolved and "
                     "rejected auctions). The 30-year tenor cleared in 2026 at a 4-6 bps greenium on insurer "
                     "demand, and the H2 FY27 calendar puts all green supply into 30-year bonds."),
    }


@app.get("/sll/kpis", tags=["Analytics"], summary="How transparent are sustainability-linked loan KPIs?")
def sll_kpis():
    sll = DEALS[DEALS.instrument.isin(["Sustainability-linked loan", "Sustainability-linked bond"])]
    rows = []
    for _, r in sll.iterrows():
        text = str(r.use_of_proceeds_or_kpis)
        named = "KPIs:" in text and "not disclosed" not in text.lower()
        rows.append({"deal_id": r.deal_id, "issuer": r.issuer, "usd_mn": round(float(r.usd_mn), 1),
                     "kpi_disclosure": text, "kpis_named": named, "source_url": r.source_url})
    return {"count": len(rows), "with_named_kpis": sum(r["kpis_named"] for r in rows), "deals": rows}


@app.get("/fx", tags=["System"], summary="FX rates used for conversion (units per USD)")
def fx():
    return {"units_per_usd": FX, "note": "Fixed approximate Oct 2026 rates; not deal-date rates."}
