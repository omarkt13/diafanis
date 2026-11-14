# Waypoint

Personal flight search for one user: cash fares, award seats and fare tricks in one ranked list.
See README.md for what a search does and how to run it.

## Layout

- `backend/` FastAPI. `app/sources/` are API clients (Seats.aero, SerpApi). `app/engine/` is the logic:
  `awards.py` (joins award legs), `tricks.py` (return-ticket and hidden-city fares), `geo.py` (hub choice).
- `frontend/` React + TypeScript + Tailwind v4, package manager bun. `bun run build` writes to `static/`,
  which FastAPI serves. `src/routes.ts` groups all fares by flights (one row for each route, all cabins) and holds the
  ranking for the three views: lowest cost, best value (`VALUE` parameters) and tricks. `src/useLeg.ts` loads one direction.
- Tests: `cd backend && .venv/bin/python -m pytest`. No test calls a live API.

## Rules

- Cash fares come from Google Flights directly (`app/sources/google_flights.py`, libraries `fast-flights` and `fli`):
  free, no key. `CASH_SOURCE=serpapi` plus `SERPAPI_KEY` selects the paid SerpApi client, which has the same methods.
- Keys: `SEATS_AERO_KEY` from the environment or `backend/.env`. Never commit keys. In the cloud environment the
  proxy adds the Seats.aero key, and `www.google.com` must be an allowed host for cash fares.
- Seats.aero calls cost quota and Google can block heavy use. Keep calls behind the cache and state the call count of new features.
- Every award row must show its data age. Fare tricks must keep their risk text.
- The user reads reports in ASD-STE100 Simplified Technical English.
- The user runs the app all the time on their own computer (`scripts/install-service.sh` or `docker compose`),
  later possibly on a small server on Tailscale.

## Open work

- `scripts/install-service.sh` is not yet run on a real macOS or Linux desktop.
- `app/data/transfers.json` needs the user's real cards and transfer partners.
- The Google page format can change. `parse_page` skips rows it cannot read; `tests/fixtures/google_page_*.json` are real pages.
