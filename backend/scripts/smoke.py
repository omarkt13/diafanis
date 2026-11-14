"""Live check of both data sources. Uses 1 Seats.aero call and 1 cash fare search.

Run from backend/:  .venv/bin/python -m scripts.smoke [ORIGIN DEST YYYY-MM-DD]
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from app.cache import Cache
from app.config import load_settings
from app.sources.seats_aero import SeatsAeroClient
from app.sources.google_flights import GoogleFlightsClient
from app.sources.serpapi_flights import SerpApiFlightsClient


async def main() -> int:
    origin, dest = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("DXB", "GVA")
    day = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else date.today() + timedelta(days=21)
    settings, cache, ok = load_settings(), Cache(":memory:"), True

    try:
        rows = await SeatsAeroClient(settings, cache).search([origin], [dest], day, day)
        print(f"PASS Seats.aero: {len(rows)} availability rows for {origin}-{dest} on {day}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"FAIL Seats.aero: {exc}")

    if settings.cash_source == "serpapi":
        cash, label = SerpApiFlightsClient(settings, cache), "SerpApi"
    else:
        cash, label = GoogleFlightsClient(cache), "Google Flights (direct)"
    if not cash.configured:
        ok = False
        print(f"FAIL {label}: SERPAPI_KEY is not set")
    else:
        try:
            res = await cash.one_way(origin, dest, day, "business", "USD")
            airlines = sorted({a for it in res.itineraries for a in it.airlines})
            print(f"PASS {label}: {len(res.itineraries)} business fares, lowest {res.lowest_price}, "
                  f"usual range {res.typical_range}, airlines: {', '.join(airlines)}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"FAIL {label}: {exc}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
