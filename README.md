# Waypoint

Personal flight search: award seats, cash fares, and (next) hidden-city and return-fare checks.

## What works now

- **Award seats** (Seats.aero Partner API). One search makes 3 API calls:
  origin to destination, origin to hubs, hubs to destination. The engine joins
  two legs of the same program and cabin when the connection is 1 to 24 hours.
  Seats.aero stores seats per airport pair, so Turkish DXB-IST-GVA only shows as two legs.
- **Cash fares** (SerpApi Google Flights). Code is in place; it is not tested
  against live data yet.
- **Web UI**: search bar, cabin tabs, date strip with the lowest miles per day,
  filters, expandable rows with flights, data age and a link to the program.

## Run

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd frontend && bun install && bun run build
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000. For UI work, run `bun run dev` in `frontend/` (it sends `/api` to port 8000).

## Keys

Put them in `backend/.env` (ignored by git):

```
SEATS_AERO_KEY=...
SERPAPI_KEY=...
```

In the cloud dev environment the proxy adds the Seats.aero key itself.
SerpApi accepts the key only as a URL parameter, so `SERPAPI_KEY` must be set.

## Tests

```bash
cd backend && .venv/bin/python -m pytest
```
