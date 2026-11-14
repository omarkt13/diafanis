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

## Data sources and cost

| Data | Source | Cost |
|---|---|---|
| Award seats, joined awards | Seats.aero Pro API | 3 calls for each direction, limit 1,000 each day |
| Cash fares, round-trip prices, fare tricks | Google Flights, read directly with the open-source libraries `fast-flights` and `fli` | Free, no key |

A one-way search sends approximately 14 requests to Google and a round trip approximately 24. Cash results are
cached for 2 hours (`CASH_CACHE_MINUTES`). Google can slow down or block a computer that sends too many
requests. If that occurs, the page shows awards only and a note. Wait, or set `CASH_SOURCE=serpapi` with a
`SERPAPI_KEY` to use the paid source.

## Run it all the time on your computer

1. Make the settings file and put your Seats.aero key in it:

```bash
cp backend/.env.example backend/.env
```

2. Start it as a service. Use one of these.

macOS or Linux, no Docker (needs Python 3.11+ and bun or npm):

```bash
scripts/install-service.sh
```

All systems, with Docker:

```bash
docker compose up -d --build
```

3. Open http://127.0.0.1:8000. The app starts again after a restart of the computer.

To try it one time without a service, run `./run.sh`.

### Reach it from your other devices (Tailscale)

- Service script: add `HOST=0.0.0.0` and `APP_PASSWORD=...` to `backend/.env`, then run `scripts/install-service.sh` again.
- Docker: put `WAYPOINT_BIND=0.0.0.0` in a file `.env` next to `docker-compose.yml`, add `APP_PASSWORD=...` to `backend/.env`, then run `docker compose up -d`.
- Open `http://<tailscale name of the computer>:8000`. The browser asks for the password (any user name).

The same steps work on a small server.

## Update

```bash
git pull
```

Then run the service command again (`scripts/install-service.sh` or `docker compose up -d --build`).

## Check the data sources

```bash
cd backend && .venv/bin/python -m scripts.smoke
```

This uses 1 Seats.aero call and 1 cash fare search.

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
- A premium or first fare can have a flight in a lower cabin. The row shows "Mixed cabin" with those flights.
- A hidden-city fare shows only when Google lists a ticket that connects at your destination. This is rare when the destination is not a hub (GVA), and common when it is (DXB).
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
