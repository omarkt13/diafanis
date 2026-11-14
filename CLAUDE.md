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

- Keys: `SEATS_AERO_KEY` and `SERPAPI_KEY` from the environment or `backend/.env`. Never commit them.
  In the cloud environment the proxy adds the Seats.aero key. SerpApi takes the key only as a URL parameter,
  so it needs the `SERPAPI_KEY` variable.
- Each external call costs quota. Keep calls behind the cache and state the call count of new features.
- Every award row must show its data age. Fare tricks must keep their risk text.
- The user reads reports in ASD-STE100 Simplified Technical English.

## Open work

- SerpApi was checked live on 2026-11-14 (DXB-GVA, 2026-11-27, return 2026-12-04). `tests/fixtures/serpapi_one_way.json`
  is a real response. Facts from that check: `show_hidden=true` gives the full fare list (69 fares where the short list
  has 9); some itineraries have no `price`; a round-trip price is the total with the lowest-cost return; a search with
  several destinations in `arrival_id` gives the end airport of each itinerary in its last flight.
- Not done: no test fixture for a round-trip or a multi-destination response. Add them if that code changes.
- The hidden-city search finds nothing when the destination is not a hub. It still costs 1 search for each cabin.
  A possible change: skip it when the destination is not in `HUBS`.
- `app/data/transfers.json` needs the user's real cards and transfer partners.
