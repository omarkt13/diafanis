"""Cash fares read directly from Google Flights. No key and no cost for each search.

Two open-source libraries do the requests:
- fast-flights loads the Google Flights page. The page holds Google's short
  list (about 9 fares), the "best" marks and the usual price range.
- fli (PyPI name "flights") calls the request that the page makes for
  "View more flights". It gives the full list and takes several destinations.

Google can slow down or block a computer that sends many requests, so results
are cached for longer than paid results and requests are spaced out.
"""
from __future__ import annotations

import asyncio
import json
import random
from datetime import date
from typing import Any

from app.cache import Cache
from app.sources.serpapi_flights import CashItinerary, CashSearchResult, CashSegment, SerpApiError, call_counter

CABIN_CODE = {"economy": 1, "premium": 2, "business": 3, "first": 4}
CABIN_NAME = {1: "Economy", 2: "Premium Economy", 3: "Business", 4: "First"}
FF_SEAT = {"economy": "economy", "premium": "premium-economy", "business": "business", "first": "first"}
MAX_PARALLEL = 3


class GoogleFlightsError(SerpApiError):
    """Same base as the SerpApi error, so the API routes handle both sources alike."""


def _hm(value: list | None) -> str:
    # Google drops zero parts: [8] is 08:00 and [None, 31] is 00:31.
    padded = [*(value or []), None, None]
    return f"{padded[0] or 0:02d}:{padded[1] or 0:02d}"


def _ymd(value: list) -> str:
    return f"{value[0]:04d}-{value[1]:02d}-{value[2]:02d}"


def parse_page(payload: list, cabin: str, currency: str) -> tuple[list[CashItinerary], dict[str, Any]]:
    """Read fares and price insights from the data block of a Google Flights page."""
    want = CABIN_CODE[cabin]
    out: list[CashItinerary] = []
    for index, best in ((2, True), (3, False)):
        section = payload[index] if len(payload) > index else None
        for row in (section[0] if section and section[0] else []):
            try:
                flight, price = row[0], row[1][0][1]
                segs, other = [], []
                for s in flight[2]:
                    code, number = s[22][0], s[22][1]
                    seg = CashSegment(
                        flight_number=f"{code} {number}", airline=s[22][3] or code, origin=s[3], destination=s[6],
                        departs_at=f"{_ymd(s[20])}T{_hm(s[8])}", arrives_at=f"{_ymd(s[21])}T{_hm(s[10])}",
                        duration_minutes=int(s[11] or 0), aircraft=s[17], travel_class=CABIN_NAME.get(s[16]),
                    )
                    segs.append(seg)
                    if s[16] and s[16] != want:
                        other.append(f"{seg.flight_number} {CABIN_NAME.get(s[16], '')}".strip())
                if not segs or len(other) == len(segs) or not price:
                    continue
                out.append(CashItinerary(
                    price=float(price), currency=currency, departs_at=segs[0].departs_at, arrives_at=segs[-1].arrives_at,
                    duration_minutes=int(flight[9] or 0), stops=len(segs) - 1, via=[s.destination for s in segs[:-1]],
                    airlines=list(dict.fromkeys(s.airline for s in segs)), segments=segs, best=best,
                    booking_token=None, other_cabin=other,
                ))
            except (IndexError, TypeError, ValueError):
                continue  # a row in a shape we do not know: skip it, keep the others

    insights: dict[str, Any] = {}
    try:
        block = payload[5]
        low, high = block[4][1], block[5][1]
        lowest = block[1][1]
        if low and high:
            insights["typical_range"] = [float(low), float(high)]
            if lowest:
                insights["price_level"] = "low" if lowest < low else "high" if lowest > high else "typical"
        if lowest:
            insights["lowest_price"] = float(lowest)
    except (IndexError, TypeError):
        pass
    return out, insights


def _fetch_page(origin: str, destination: str, day: date, cabin: str, currency: str, return_date: date | None) -> list:
    from fast_flights import FlightQuery, create_query, fetch_flights_html
    from selectolax.lexbor import LexborHTMLParser

    flights = [FlightQuery(date=day.isoformat(), from_airport=origin, to_airport=destination)]
    if return_date:
        flights.append(FlightQuery(date=return_date.isoformat(), from_airport=destination, to_airport=origin))
    query = create_query(flights=flights, seat=FF_SEAT[cabin], trip="round-trip" if return_date else "one-way", language="en", currency=currency)
    html = fetch_flights_html(query)
    script = LexborHTMLParser(html).css_first(r"script.ds\:1")
    if script is None:
        raise GoogleFlightsError("Google did not send flight data (possible block or consent page)")
    data = script.text().split("data:", 1)[1].rsplit(",", 1)[0]
    if data.endswith("errorHasStatus: true"):
        return []
    return json.loads(data)


def _fetch_full(origin: str, destinations: list[str], day: date, cabin: str, currency: str) -> list[CashItinerary]:
    from fli.models import Airport, FlightSearchFilters, FlightSegment, MaxStops, PassengerInfo, SeatType, SortBy
    from fli.search import SearchFlights

    seat = {"economy": SeatType.ECONOMY, "premium": SeatType.PREMIUM_ECONOMY, "business": SeatType.BUSINESS, "first": SeatType.FIRST}[cabin]
    try:
        segment = FlightSegment(
            departure_airport=[[getattr(Airport, origin), 0]],
            arrival_airport=[[getattr(Airport, d), 0] for d in destinations],
            travel_date=day.isoformat(),
        )
    except AttributeError as exc:
        raise GoogleFlightsError(f"Airport not known to the full-list search: {exc}") from exc
    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(adults=1), flight_segments=[segment], seat_type=seat,
        stops=MaxStops.ANY, sort_by=SortBy.CHEAPEST, show_all_results=True,
    )
    out: list[CashItinerary] = []
    for r in SearchFlights().search(filters, currency=currency) or []:
        if isinstance(r, tuple) or not r.price or not r.legs:
            continue
        segs = [
            CashSegment(
                flight_number=f"{leg.airline.name.lstrip('_')} {leg.flight_number}", airline=str(leg.airline.value),
                origin=leg.departure_airport.name, destination=leg.arrival_airport.name,
                departs_at=leg.departure_datetime.isoformat()[:16], arrives_at=leg.arrival_datetime.isoformat()[:16],
                duration_minutes=int(leg.duration or 0), aircraft=getattr(leg, "aircraft", None), travel_class=None,
            )
            for leg in r.legs
        ]
        out.append(CashItinerary(
            price=float(r.price), currency=currency, departs_at=segs[0].departs_at, arrives_at=segs[-1].arrives_at,
            duration_minutes=int(r.duration or 0), stops=len(segs) - 1, via=[s.destination for s in segs[:-1]],
            airlines=list(dict.fromkeys(s.airline for s in segs)), segments=segs, best=False,
            booking_token=getattr(r, "booking_token", None),
            other_cabin=["one or more flights in a different cabin"] if getattr(r, "mixed_cabin", False) else [],
        ))
    return out


def merge(page: list[CashItinerary], full: list[CashItinerary]) -> list[CashItinerary]:
    """One entry for each set of flights. The page entry wins: it has the cabin of each flight."""
    by_key: dict[tuple[str, ...], CashItinerary] = {}
    for it in [*page, *full]:
        key = tuple(s.flight_number.replace(" ", "") for s in it.segments)
        old = by_key.get(key)
        if old is None:
            by_key[key] = it
        elif it.price is not None and (old.price is None or it.price < old.price):
            by_key[key] = old.model_copy(update={"price": it.price})
    return sorted(by_key.values(), key=lambda i: (not i.best, i.price or 0))


class GoogleFlightsClient:
    def __init__(self, cache: Cache, cache_minutes: int = 120):
        self._cache = cache
        self._ttl = cache_minutes * 60
        self._gate = asyncio.Semaphore(MAX_PARALLEL)
        self.calls_made = 0

    configured = True
    name = "google flights (direct)"

    async def one_way(self, origin: str, destination: str, day: date, cabin: str, currency: str) -> CashSearchResult:
        return await self.search(origin, [destination], day, cabin, currency)

    async def search(
        self, origin: str, destinations: list[str], day: date, cabin: str, currency: str, return_date: date | None = None,
    ) -> CashSearchResult:
        origin, dests = origin.upper(), [d.upper() for d in destinations]
        dest = ",".join(dests)
        key = f"gflights:{origin}:{dest}:{day}:{cabin}:{currency}:{return_date or ''}"
        cached = self._cache.get(key)
        if cached is not None:
            return CashSearchResult(**cached)

        page: list[CashItinerary] = []
        full: list[CashItinerary] = []
        insights: dict[str, Any] = {}
        errors: list[str] = []

        async def run(fn, *args):
            async with self._gate:
                await asyncio.sleep(random.uniform(0.1, 0.6))  # do not send requests in one burst
                self.calls_made += 1
                counter = call_counter.get()
                if counter is not None:
                    counter[0] += 1
                return await asyncio.to_thread(fn, *args)

        jobs = []
        if len(dests) == 1:
            jobs.append(("page", run(_fetch_page, origin, dests[0], day, cabin, currency, return_date)))
        if not return_date:
            jobs.append(("full", run(_fetch_full, origin, dests, day, cabin, currency)))
        results = await asyncio.gather(*(j for _, j in jobs), return_exceptions=True)
        for (kind, _), res in zip(jobs, results):
            if isinstance(res, Exception):
                errors.append(f"{kind}: {res}")
            elif kind == "page":
                page, insights = parse_page(res, cabin, currency) if res else ([], {})
            else:
                full = res
        if len(errors) == len(jobs):
            raise GoogleFlightsError("Google Flights search failed. " + " | ".join(e[:200] for e in errors))

        itineraries = merge(page, full)
        prices = [i.price for i in itineraries if i.price]
        result = CashSearchResult(
            origin=origin, destination=dest, date=day.isoformat(), cabin=cabin, currency=currency, itineraries=itineraries,
            lowest_price=min(prices) if prices else insights.get("lowest_price"),
            price_level=insights.get("price_level"), typical_range=insights.get("typical_range"),
        )
        if itineraries:
            self._cache.set(key, result.model_dump(), self._ttl)
        return result
