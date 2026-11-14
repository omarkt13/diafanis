# Waypoint

A personal flight search. You enter a route and a date one time. The tool searches
cash fares, award seats and fare tricks in all cabins, and ranks them in one list.

## What one search does

| Find | How | Source |
|---|---|---|
| Cash fares in 4 cabins | 4 searches | SerpApi Google Flights |
| Award seats, date ± 1 to 3 days | 1 search | Seats.aero |
| Joined awards (for example Turkish via IST) | 2 searches: origin to hubs, hubs to destination. Legs of one program and cabin are joined when the connection is 1 to 24 hours | Seats.aero |
| Return ticket cheaper than one way | Round-trip searches with return 7 and 14 days later, compared with the one-way on the same flights | SerpApi |
| Hidden-city fare | 1 search to 7 large airports near the destination. Trips that connect at the destination and cost less are kept | SerpApi |
| Value of miles | (cash fare − award taxes) ÷ miles | both |
| Awards you can book now | Your balances and transfer partners | `backend/app/data/transfers.json` |

One search uses 3 Seats.aero calls (limit 1,000 each day) and 7 SerpApi searches
(4 cabins + 3 for fare tricks in the cabin in view). Results are cached for 30 minutes.

## Run

```bash
cp backend/.env.example backend/.env
```

Put your two keys in `backend/.env`, then:

```bash
./run.sh
```

Open http://127.0.0.1:8000. The server listens on your computer only. It has no login,
so do not put it on the public internet as it is.

## Check the data sources

```bash
cd backend && .venv/bin/python -m scripts.smoke
```

This uses 1 Seats.aero call and 1 SerpApi search, and saves the SerpApi response as a test fixture.

## Your points

Open **My points** in the page and enter your balances. They stay in your browser.
The transfer partners in `backend/app/data/transfers.json` are a start only
(Marriott Bonvoy, and the United States list of Amex Membership Rewards).
Add your own cards there: `"ratio"` is the number of points for 1 mile.

## Limits

- Award data is a cache. Each row shows its age. Check the seats on the program site before you transfer points.
- Award taxes in dollars use fixed exchange rates (`USD_PER` in `backend/app/engine/awards.py`).
- Cash fares and fare tricks are for the selected date only.
- A hidden-city or return-ticket fare breaks airline ticket rules. The page shows the risks on each one.
- The tool does not book. It links to the program or to Google Flights.

## Develop

```bash
cd backend && .venv/bin/python -m pytest
```

```bash
cd frontend && bun run dev
```

UI work without SerpApi searches: `backend/scripts/fake_serpapi.py` gives made-up fares in the SerpApi format.
