"""Live check of both data sources. Uses 1 Seats.aero call and 1 SerpApi search.

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

    serp = SerpApiFlightsClient(settings, cache)
    if not serp.configured:
        ok = False
        print("FAIL SerpApi: SERPAPI_KEY is not set")
    else:
        try:
            raw = await serp._get({"engine": "google_flights", "departure_id": origin, "arrival_id": dest,
                                   "outbound_date": day.isoformat(), "type": "2", "travel_class": "3", "currency": "USD", "hl": "en", "show_hidden": "true"})
            res = await serp.one_way(origin, dest, day, "business", "USD")
            airlines = sorted({a for it in res.itineraries for a in it.airlines})
            print(f"PASS SerpApi: {len(res.itineraries)} business fares, lowest {res.lowest_price}, airlines: {', '.join(airlines)}")
            out = Path(__file__).parent.parent / "tests" / "fixtures"
            out.mkdir(exist_ok=True)
            raw.pop("search_metadata", None), raw.pop("search_parameters", None)
            (out / "serpapi_one_way.json").write_text(json.dumps(raw, indent=1))
            print(f"     saved the response to {out / 'serpapi_one_way.json'} for tests")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"FAIL SerpApi: {exc}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
