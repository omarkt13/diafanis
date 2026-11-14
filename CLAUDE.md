# Waypoint

Personal flight search for one user: cash fares, award seats and fare tricks in one ranked list.
See README.md for what a search does and how to run it.

## Layout

- `backend/` FastAPI. `app/sources/` are API clients (Seats.aero, SerpApi). `app/engine/` is the logic:
  `awards.py` (joins award legs), `tricks.py` (return-ticket and hidden-city fares), `geo.py` (hub choice).
- `frontend/` React + TypeScript + Tailwind v4, package manager bun. `bun run build` writes to `static/`,
  which FastAPI serves. `src/ways.ts` merges all sources into one list and makes the "Found for you" cards.
- Tests: `cd backend && .venv/bin/python -m pytest`. No test calls a live API.

## Rules

- Keys: `SEATS_AERO_KEY` and `SERPAPI_KEY` from the environment or `backend/.env`. Never commit them.
  In the cloud environment the proxy adds the Seats.aero key. SerpApi takes the key only as a URL parameter,
  so it needs the `SERPAPI_KEY` variable.
- Each external call costs quota. Keep calls behind the cache and state the call count of new features.
- Every award row must show its data age. Fare tricks must keep their risk text.
- The user reads reports in ASD-STE100 Simplified Technical English.

## Open work

- The SerpApi code (cash fares, fare tricks) was written from the documentation and tested with a stand-in
  server only. In a session that has `SERPAPI_KEY`: run `python -m scripts.smoke` from `backend/`, fix
  what differs, and add a test on the saved fixture. Check if Turkish Airlines fares show for DXB-GVA.
- `app/data/transfers.json` needs the user's real cards and transfer partners.
