# Diafanis

**Independent valuation estimates for private market funds.**

Diafanis is a browse-only intelligence tool for LPs — especially individual
investors on feeder platforms (Moonfare-style) who hold, or are considering
buying/selling secondaries in, private funds and lack independent tools to
verify what their advisors tell them.

It covers ~150 flagship funds from ~50 marquee sponsors across four asset
classes — PE buyout, venture capital, real assets & infrastructure, and
private credit — and estimates each fund's current value from public market
data, refreshed daily.

## How the model works

For every fund, a simplified Takahashi-Alexander pacing model simulates
quarterly cashflows from vintage to today:

- **Contributions** are drawn over the investment period.
- **Deployed capital compounds** at the fund's sector-weighted public
  benchmark return (baskets of listed comps: software, healthcare,
  infrastructure, BDCs/HY credit, growth proxies…), scaled by an asset-class
  beta plus a GP alpha spread.
- **Distributions** pace up from mid-life; credit funds distribute income
  from year one.
- **Fees** (2%/20% over an 8% pref) reduce everything to net-of-fee.
- **Calibration**: where a fund has a genuinely public reported mark (pension
  disclosures, GP reports), the model is solved to pass through that mark and
  then rolled forward on benchmark returns — *"public benchmark roll-forward
  from the last disclosed mark."*

Outputs per fund: estimated TVPI/MOIC, DPI, RVPI, NAV, net IRR, and
Kaplan-Schoar PME alpha versus the fund's own blended benchmark, plus a
quarterly estimate-of-value series (the graph). Every estimate carries a
confidence tag (high = calibrated to a public mark, medium = GP track record,
low = pacing model only).

**All output is model-estimated, not GP-reported. Fund names, sizes and marks
in the seed dataset are indicative figures compiled from public sources. This
is not investment advice.**

## Stack

- **Backend**: FastAPI + SQLAlchemy (SQLite), yfinance (comp prices), FRED
  (macro), APScheduler (daily refresh), DeepSeek API (plain-English fund
  narratives; deterministic fallback without a key).
- **Frontend**: React + TypeScript + Vite + Tailwind, recharts for the
  estimate-of-value graph. Built assets are served by FastAPI from `static/`.

## Running locally

```bash
# Backend (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```

On first boot the app seeds the fund universe and computes valuations for all
funds (deterministic fallback data if offline). API docs at
`http://localhost:8000/docs`.

```bash
# Frontend (dev mode, proxies /api to :8000)
cd frontend-react
bun install
bun run dev
```

Or build once and let FastAPI serve everything on :8000:

```bash
cd frontend-react && bun run build
```

Optional env vars (see `backend/.env.example`): `FRED_API_KEY` for live macro
data, `DEEPSEEK_API_KEY` for AI-generated narratives.

## Tests

```bash
cd backend && python -m pytest
```
