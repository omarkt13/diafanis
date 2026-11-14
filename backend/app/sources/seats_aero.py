from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.cache import Cache
from app.config import Settings

CACHE_TTL_SECONDS = 30 * 60
PAGE_SIZE = 1000
MAX_PAGES = 5


class SeatsAeroError(RuntimeError):
    pass


class SeatsAeroClient:
    """Client for the Seats.aero Partner API (cached award availability).

    One search call accepts several origin and destination airports. With
    include_trips=true each availability row also carries its flights, which
    lets the engine check connection times without extra calls.
    """

    def __init__(self, settings: Settings, cache: Cache, http: httpx.AsyncClient | None = None):
        self._settings = settings
        self._cache = cache
        self._http = http or httpx.AsyncClient(timeout=60)
        self.rate_limit_remaining: int | None = None
        self.calls_made = 0

    def _headers(self) -> dict[str, str]:
        # With no key set, send no header: the cloud proxy adds it.
        if self._settings.seats_aero_key:
            return {"Partner-Authorization": self._settings.seats_aero_key}
        return {}

    async def search(
        self,
        origins: list[str],
        destinations: list[str],
        start: date,
        end: date,
        sources: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "origin_airport": ",".join(sorted(set(origins))),
            "destination_airport": ",".join(sorted(set(destinations))),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "take": str(PAGE_SIZE),
            "include_trips": "true",
        }
        if sources:
            params["sources"] = ",".join(sorted(set(sources)))

        cache_key = "seats.search:" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        for _ in range(MAX_PAGES):
            body = await self._get("/search", params)
            rows.extend(body.get("data") or [])
            if not body.get("hasMore") or not body.get("cursor"):
                break
            params = {**params, "cursor": str(body["cursor"]), "skip": str(len(rows))}

        self._cache.set(cache_key, rows, CACHE_TTL_SECONDS)
        return rows

    async def trip_details(self, availability_id: str) -> dict[str, Any]:
        cache_key = f"seats.trips:{availability_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        body = await self._get(f"/trips/{availability_id}", {})
        self._cache.set(cache_key, body, CACHE_TTL_SECONDS)
        return body

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        resp = await self._http.get(self._settings.seats_aero_base + path, params=params, headers=self._headers())
        self.calls_made += 1
        remaining = resp.headers.get("X-Ratelimit-Remaining")
        if remaining is not None and remaining.isdigit():
            self.rate_limit_remaining = int(remaining)
        if resp.status_code != 200:
            raise SeatsAeroError(f"Seats.aero {path} returned {resp.status_code}: {resp.text[:200]}")
        return resp.json()
