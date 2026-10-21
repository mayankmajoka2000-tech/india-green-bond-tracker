# India Green Bond & ESG Loan Tracker

A deal-level tracker of **labelled green, ESG and sustainability-linked debt raised by Indian issuers**,
covering sovereign green bond auctions, PSU lenders, banks, corporates and municipalities from
January 2023 to October 2026. Built in Python with a formula-driven Excel front end.

📊 **Workbook:** [`output/India_Green_Finance_Tracker.xlsx`](output/India_Green_Finance_Tracker.xlsx)
📁 **Data:** [`data/deals.csv`](data/deals.csv), 25 deals, each linked to its public source

## What's inside

| Sheet | Contents |
|---|---|
| Dashboard | Totals, splits by instrument / issuer type / year, and charts. Everything is a live formula |
| Deals | One row per deal: issuer, instrument, amount, pricing, tenor, lenders, use of proceeds or KPIs, status, source |
| Sovereign Greenium | Every sovereign green bond auction outcome and the greenium achieved |
| FX | Conversion rates (editable). Changing a rate re-prices every deal |
| About | Scope, definitions and limitations |

## Headline numbers (23 completed deals)

| | USD mn | Share |
|---|---|---|
| Green bonds | 3,120 | 52% |
| Green loans | 1,808 | 30% |
| Sustainability-linked loans | 1,050 | 17% |
| ESG bonds | 57 | 1% |
| **Total** | **6,035** | (about Rs 53,100 crore at Rs 88/USD) |

By issuer: Sovereign 32%, Corporate 28%, PSU NBFCs 27%, Banks 12%, Municipal 1%.

## Key findings

1. **The sovereign green bond market found its footing only at 30 years.** Between May 2024 and June 2025
   the government cancelled one auction, saw two devolve on primary dealers, and rejected every bid at
   another, because banks would not pay a premium for green 5- and 10-year paper. In 2026 the 30-year tenor
   cleared with a **4-6 bps greenium**, the largest since the 2023 debut, driven by insurers, which can count
   the bonds as infrastructure investment. The government has put the entire H2 FY27 green calendar
   (Rs 15,000 crore) into 30-year bonds. Outstanding sovereign green bonds: **Rs 877 bn** (Aug 2026).

2. **Sustainability-linked loans are opaque about their KPIs.** Of the three SLLs tracked, only L&T's
   US$700 mn facility with Standard Chartered names its targets (GHG intensity and fresh-water withdrawal).
   Tata Communications cites "carbon emission reduction targets", and JK Tyre's US$100 mn IFC loan
   discloses none. Without KPIs and step-up terms, an investor or lender can't judge how ambitious a deal is.

3. **Development finance carries the loan market.** Development finance institutions or export credit
   agencies (IFC, JBIC, AFD, FMO, EDC, Clean Technology Fund) are lenders on **7 of the 10 loans** tracked.
   Only three (Zelestra, Serentica and L&T) were funded by commercial banks alone.

4. **Municipal green bonds are small but multiplying.** Ghaziabad, Pimpri-Chinchwad and Surat all issued in 2025,
   Surat at 8.00% with AA+ ratings, to fund solar, wind, e-bus depots and water treatment. Together they are
   under 1% of the volume tracked.

5. **Labelling is inconsistent.** IREDA's 2025 perpetual and Tier II bonds are reported as green by trade press
   but not by IREDA itself, so they are flagged *Unconfirmed*. L&T's Rs 500 crore issue is labelled ESG
   rather than green. Labels matter for whether investors can count the bonds towards green mandates.

## API

The tracker is also a FastAPI service (`api/main.py`, interactive docs at `/docs`).

| Endpoint | Returns |
|---|---|
| `GET /deals` | Filter by `instrument`, `issuer_type`, `status`, `year`, `since`/`until`, `issuer`, `min_usd_mn`; sort by date or size |
| `GET /deals/{deal_id}` | One deal with pricing, lenders, use of proceeds or KPIs, and source |
| `GET /summary?since=&until=` | Totals and shares by instrument, issuer type and year; largest deal |
| `GET /issuers` | Issuers ranked by green / ESG debt raised |
| `GET /sovereign/auctions` | Every sovereign green bond auction outcome |
| `GET /sovereign/greenium` | Greenium history, failed auctions and the takeaway |
| `GET /sll/kpis` | Which sustainability-linked loans actually disclose their KPIs |
| `GET /fx` | Conversion rates used |

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload        # http://127.0.0.1:8000/docs
pytest -q                            # 9 tests
```

Deploy: `render.yaml` (Render free tier) or `Dockerfile`.

## Command line

```bash
pip install pandas openpyxl
python tracker.py summary                               # totals by instrument, issuer type, year
python tracker.py list --type "Green loan" --since 2025-01-01
python tracker.py excel                                 # rebuild the workbook from data/deals.csv
```

To add a deal, append a row to `data/deals.csv` (amount in millions of the deal currency) or type it into
an empty yellow row of the Deals sheet. The Dashboard updates automatically.

## Definitions

- **Completed** = Priced, Signed or Devolved. *Rejected* and *Scheduled* rows are kept for context and excluded from totals.
- **Greenium** = how much lower the green bond's yield is than a comparable conventional government bond, in basis points.
- **FX**: all deals are converted at current rates on the FX sheet, not at each deal date's rate, so totals are indicative.

## Limitations

This is a curated sample assembled from public filings and news, not a complete market database such as
Bloomberg, LSEG or the Climate Bonds Initiative. Where a source gives no amount, the deal is listed and left out of totals.

---
*Mayank Majoka, October 2026. Not investment advice.*
