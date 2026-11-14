# Waypoint

A personal flight search. You enter a route and a date one time. The tool searches
cash fares, award seats and fare tricks in all cabins, and ranks them in one list.

## How it works

You enter the airports and the date (or two dates for a round trip). The search is the same for
all cabins. Each result row is one set of flights, with its cash fare and its best award in each
of the four cabins. Open a row to see every fare and program for those flights.

Three views:

- **Lowest cost**: rows in order of the lowest cost in dollars. Miles count at the value you set (default 1.2 cents), plus award taxes.
- **Best value**: cost for what you get. A business seat counts as 3× economy, premium 1.5×, first 4.5×. Each stop adds $30 and each hour above the fastest route adds $15. Old award data ranks lower. The parameters are `VALUE` in `frontend/src/routes.ts`.
- **Tricks**: a separate list, always in order of cost: return ticket flown one way, hidden-city ticket, two award legs joined at a hub, a seat through the program of another airline, and (round trip) two one-way tickets or a mix of cash and miles.

## What one search costs

| Search | Calls |
|---|---|
| Award seats and joined awards, each direction | 3 Seats.aero calls (limit 1,000 each day) |
| Cash fares in 4 cabins, each direction | 4 SerpApi searches |
| Fare tricks, economy and business, each direction | 6 SerpApi searches one way, 2 for a round trip |
| Round-trip ticket prices in 4 cabins | 4 SerpApi searches |

A one-way search uses 3 Seats.aero calls and 10 SerpApi searches. A round trip uses 6 and 16.
Results are cached for 30 minutes.

## Run

```bash
cp backend/.env.example backend/.env
```

Put your two keys in `backend/.env`, then:

```bash
./run.sh
```

Open http://127.0.0.1:8000. The server listens on your computer only.

## Host it

The repo has a `Dockerfile` and a `render.yaml` blueprint. On a host, set three values:
`SEATS_AERO_KEY`, `SERPAPI_KEY` and `APP_PASSWORD`. With `APP_PASSWORD` set, the browser asks for
that password (any user name). Do not host the app without it: each search uses your API quota.

```bash
docker build -t waypoint .
```

```bash
docker run -p 8000:8000 --env-file backend/.env -e APP_PASSWORD=change-me waypoint
```

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
- Cash fares and fare tricks are for the search date only. Other dates in the date strip show awards only.
- Fare tricks run for economy and business only.
- A round trip is priced as two directions. The table above the list compares one return ticket, two one-way tickets, and a mix of cash and miles.
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
