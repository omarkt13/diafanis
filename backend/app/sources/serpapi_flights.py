from __future__ import annotations

from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel

from app.cache import Cache
from app.config import Settings

CACHE_TTL_SECONDS = 30 * 60
TRAVEL_CLASS = {"economy": 1, "premium": 2, "business": 3, "first": 4}


class SerpApiError(RuntimeError):
    pass


class CashSegment(BaseModel):
    flight_number: str
    airline: str
    origin: str
    destination: str
    departs_at: str
    arrives_at: str
    duration_minutes: int
    aircraft: str | None
    travel_class: str | None


class CashItinerary(BaseModel):
    price: float | None
    currency: str
    departs_at: str
    arrives_at: str
    duration_minutes: int
    stops: int
    via: list[str]
    airlines: list[str]
    segments: list[CashSegment]
    best: bool
    booking_token: str | None


class CashSearchResult(BaseModel):
    origin: str
    destination: str
    date: str
    cabin: str
    currency: str
    itineraries: list[CashItinerary]
    lowest_price: float | None
    price_level: str | None
    typical_range: list[float] | None


class SerpApiFlightsClient:
    """Google Flights results through SerpApi (engine=google_flights).

    SerpApi takes the key only as the api_key URL parameter.
    """

    def __init__(self, settings: Settings, cache: Cache, http: httpx.AsyncClient | None = None):
        self._settings = settings
        self._cache = cache
        self._http = http or httpx.AsyncClient(timeout=90)
        self.calls_made = 0

    @property
    def configured(self) -> bool:
        return bool(self._settings.serpapi_key)

    async def one_way(self, origin: str, destination: str, day: date, cabin: str, currency: str) -> CashSearchResult:
        return await self.search(origin, [destination], day, cabin, currency)

    async def search(
        self,
        origin: str,
        destinations: list[str],
        day: date,
        cabin: str,
        currency: str,
        return_date: date | None = None,
    ) -> CashSearchResult:
        """One SerpApi search. Several destinations go in one call (comma list).

        With return_date the result lists outbound flights, and each price is the
        total for the round trip with the cheapest matching return.
        """
        dest = ",".join(d.upper() for d in destinations)
        params = {
            "engine": "google_flights",
            "departure_id": origin.upper(),
            "arrival_id": dest,
            "outbound_date": day.isoformat(),
            "type": "1" if return_date else "2",
            "travel_class": str(TRAVEL_CLASS[cabin]),
            "currency": currency,
            "hl": "en",
        }
        if return_date:
            params["return_date"] = return_date.isoformat()
        body = await self._get(params)
        return normalize(body, origin.upper(), dest, day.isoformat(), cabin, currency)

    async def _get(self, params: dict[str, str]) -> dict[str, Any]:
        if not self._settings.serpapi_key:
            raise SerpApiError("SERPAPI_KEY is not set")
        cache_key = "serpapi:" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        resp = await self._http.get(self._settings.serpapi_url, params={**params, "api_key": self._settings.serpapi_key})
        self.calls_made += 1
        if resp.status_code != 200:
            raise SerpApiError(f"SerpApi returned {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        if body.get("error"):
            raise SerpApiError(body["error"])
        self._cache.set(cache_key, body, CACHE_TTL_SECONDS)
        return body


def _segment(f: dict[str, Any]) -> CashSegment:
    dep, arr = f.get("departure_airport") or {}, f.get("arrival_airport") or {}
    return CashSegment(
        flight_number=f.get("flight_number") or "",
        airline=f.get("airline") or "",
        origin=dep.get("id") or "",
        destination=arr.get("id") or "",
        departs_at=(dep.get("time") or "").replace(" ", "T"),
        arrives_at=(arr.get("time") or "").replace(" ", "T"),
        duration_minutes=int(f.get("duration") or 0),
        aircraft=f.get("airplane"),
        travel_class=f.get("travel_class"),
    )


def normalize(body: dict[str, Any], origin: str, destination: str, day: str, cabin: str, currency: str) -> CashSearchResult:
    itineraries: list[CashItinerary] = []
    for key, best in (("best_flights", True), ("other_flights", False)):
        for it in body.get(key) or []:
            segs = [_segment(f) for f in it.get("flights") or []]
            if not segs:
                continue
            airlines: list[str] = []
            for s in segs:
                if s.airline and s.airline not in airlines:
                    airlines.append(s.airline)
            itineraries.append(
                CashItinerary(
                    price=it.get("price"),
                    currency=currency,
                    departs_at=segs[0].departs_at,
                    arrives_at=segs[-1].arrives_at,
                    duration_minutes=int(it.get("total_duration") or 0),
                    stops=len(segs) - 1,
                    via=[s.destination for s in segs[:-1]],
                    airlines=airlines,
                    segments=segs,
                    best=best,
                    booking_token=it.get("booking_token") or it.get("departure_token"),
                )
            )
    insights = body.get("price_insights") or {}
    prices = [i.price for i in itineraries if i.price]
    return CashSearchResult(
        origin=origin,
        destination=destination,
        date=day,
        cabin=cabin,
        currency=currency,
        itineraries=itineraries,
        lowest_price=insights.get("lowest_price") or (min(prices) if prices else None),
        price_level=insights.get("price_level"),
        typical_range=insights.get("typical_price_range"),
    )
