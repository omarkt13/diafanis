from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from app.engine.geo import distance_km, is_airport
from app.sources.serpapi_flights import CashItinerary, CashSearchResult, CashSegment, SerpApiFlightsClient

# A trick must save at least this share of the normal one-way fare to be shown.
MIN_SAVING_SHARE = 0.05
RETURN_OFFSETS_DAYS = (7, 14)
MAX_BEYOND = 7

# Large airports that tickets are often sold "through to". The hidden-city
# search prices origin -> these, and keeps trips that connect at the real
# destination.
BEYOND_POOL = [
    "LHR", "LGW", "CDG", "ORY", "AMS", "FRA", "MUC", "ZRH", "GVA", "VIE", "BRU", "MAD", "BCN", "LIS", "OPO",
    "FCO", "MXP", "VCE", "NCE", "ATH", "IST", "CPH", "ARN", "OSL", "HEL", "DUB", "MAN", "EDI", "BER", "HAM",
    "DUS", "WAW", "PRG", "BUD", "DXB", "AUH", "DOH", "RUH", "JED", "CAI", "AMM", "BAH", "KWI", "MCT", "BEY",
    "DEL", "BOM", "SIN", "BKK", "KUL", "HKG", "NRT", "ICN", "JFK", "EWR", "BOS", "IAD", "ORD", "YYZ", "YUL",
    "MIA", "ATL", "DFW", "LAX", "SFO", "CMN", "TUN", "ALG", "NBO", "ADD", "JNB",
]


class Trick(BaseModel):
    kind: Literal["return", "hidden"]
    cabin: str
    price: float
    currency: str
    normal_price: float  # the plain one-way fare this is compared with
    saving: float
    same_flights: bool  # normal_price is for the same flights (else: lowest one-way)
    itinerary: CashItinerary  # the part you fly
    ticketed_to: str | None = None  # hidden-city: where the ticket ends
    dropped: list[CashSegment] = []  # hidden-city: the flights you do not take
    return_date: str | None = None  # return: the return date of the ticket


class TrickResult(BaseModel):
    cabin: str
    tricks: list[Trick]
    beyond: list[str]
    api_calls: int
    errors: list[str]


def _flights(segs: list[CashSegment]) -> tuple[str, ...]:
    return tuple(s.flight_number.replace(" ", "").upper() for s in segs)


def pick_beyond(origin: str, destination: str, limit: int = MAX_BEYOND) -> list[str]:
    """Airports near the destination that a through ticket could end at."""
    scored = []
    for code in BEYOND_POOL:
        if code in (origin, destination) or not is_airport(code):
            continue
        d = distance_km(destination, code)
        if 150 <= d <= 2500:
            scored.append((d, code))
    return [c for _, c in sorted(scored)[:limit]]


def _baseline(one_way: CashSearchResult) -> tuple[dict[tuple[str, ...], float], float | None]:
    by_flights: dict[tuple[str, ...], float] = {}
    for it in one_way.itineraries:
        if it.price is not None:
            key = _flights(it.segments)
            by_flights[key] = min(by_flights.get(key, float("inf")), it.price)
    lowest = min(by_flights.values()) if by_flights else None
    return by_flights, lowest


def find_return_tricks(one_way: CashSearchResult, round_trips: list[tuple[str, CashSearchResult]]) -> list[Trick]:
    """Round-trip tickets that cost less than the one-way on the same outbound flights."""
    by_flights, lowest = _baseline(one_way)
    best: dict[tuple[str, ...], Trick] = {}
    for return_date, rt in round_trips:
        for it in rt.itineraries:
            if it.price is None:
                continue
            key = _flights(it.segments)
            same = key in by_flights
            normal = by_flights[key] if same else lowest
            if normal is None or it.price > normal * (1 - MIN_SAVING_SHARE):
                continue
            # Without the same flights in the one-way result, only a fare below the
            # lowest one-way is a real find.
            trick = Trick(
                kind="return", cabin=one_way.cabin, price=it.price, currency=it.currency, normal_price=normal,
                saving=round(normal - it.price, 2), same_flights=same, itinerary=it, return_date=return_date,
            )
            if key not in best or trick.price < best[key].price:
                best[key] = trick
    return sorted(best.values(), key=lambda t: t.price)


def find_hidden_city(one_way: CashSearchResult, beyond: CashSearchResult, destination: str) -> list[Trick]:
    """Tickets to a city beyond the destination that connect at the destination and cost less."""
    by_flights, lowest = _baseline(one_way)
    best: dict[tuple[str, ...], Trick] = {}
    for it in beyond.itineraries:
        if it.price is None or len(it.segments) < 2:
            continue
        cut = next((i for i, s in enumerate(it.segments[:-1]) if s.destination == destination), None)
        if cut is None:
            continue
        flown, dropped = it.segments[: cut + 1], it.segments[cut + 1 :]
        key = _flights(flown)
        same = key in by_flights
        normal = by_flights[key] if same else lowest
        if normal is None or it.price > normal * (1 - MIN_SAVING_SHARE):
            continue
        part = CashItinerary(
            price=it.price, currency=it.currency, departs_at=flown[0].departs_at, arrives_at=flown[-1].arrives_at,
            duration_minutes=_minutes(flown), stops=len(flown) - 1, via=[s.destination for s in flown[:-1]],
            airlines=list(dict.fromkeys(s.airline for s in flown if s.airline)), segments=flown, best=False, booking_token=None,
        )
        trick = Trick(
            kind="hidden", cabin=one_way.cabin, price=it.price, currency=it.currency, normal_price=normal,
            saving=round(normal - it.price, 2), same_flights=same, itinerary=part,
            ticketed_to=it.segments[-1].destination, dropped=dropped,
        )
        if key not in best or trick.price < best[key].price:
            best[key] = trick
    return sorted(best.values(), key=lambda t: t.price)


def _minutes(segs: list[CashSegment]) -> int:
    # Segment times are local and can cross time zones, so add flight time and
    # layovers measured at each connection airport (same zone on both sides).
    from datetime import datetime

    total = sum(s.duration_minutes for s in segs)
    for a, b in zip(segs, segs[1:]):
        try:
            total += int((datetime.fromisoformat(b.departs_at) - datetime.fromisoformat(a.arrives_at)).total_seconds() // 60)
        except ValueError:
            pass
    return total


async def search_tricks(
    serp: SerpApiFlightsClient, origin: str, destination: str, day: date, cabin: str, currency: str = "USD",
    include_return: bool = True,
) -> TrickResult:
    calls_before = serp.calls_made
    beyond = pick_beyond(origin, destination)
    one_way = await serp.one_way(origin, destination, day, cabin, currency)

    offsets = RETURN_OFFSETS_DAYS if include_return else ()
    jobs = [serp.search(origin, [destination], day, cabin, currency, return_date=day + timedelta(days=n)) for n in offsets]
    if beyond:
        jobs.append(serp.search(origin, beyond, day, cabin, currency))
    results = await asyncio.gather(*jobs, return_exceptions=True)

    errors = [str(r) for r in results if isinstance(r, Exception)]
    rts = [
        ((day + timedelta(days=n)).isoformat(), r)
        for n, r in zip(offsets, results)
        if isinstance(r, CashSearchResult)
    ]
    tricks = find_return_tricks(one_way, rts)
    if beyond and isinstance(results[-1], CashSearchResult):
        tricks += find_hidden_city(one_way, results[-1], destination)
    return TrickResult(cabin=cabin, tricks=tricks, beyond=beyond, api_calls=serp.calls_made - calls_before, errors=errors)
