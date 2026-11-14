from __future__ import annotations

import asyncio
import base64
import json
import secrets
from datetime import date
from functools import lru_cache
from pathlib import Path

import airportsdata

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.cache import Cache
from app.config import load_settings
from app.engine.awards import AwardSearchResult, search_awards
from app.engine.geo import HUBS, is_airport
from app.engine.programs import PROGRAMS
from app.engine.tricks import BEYOND_POOL, TrickResult, search_tricks
from app.sources.seats_aero import SeatsAeroClient, SeatsAeroError
from app.sources.google_flights import GoogleFlightsClient
from app.sources.serpapi_flights import TRAVEL_CLASS, CashSearchResult, SerpApiError, SerpApiFlightsClient

settings = load_settings()
cache = Cache(settings.cache_path)
seats = SeatsAeroClient(settings, cache)
# The cash fare source. Both clients have the same methods.
if settings.cash_source == "serpapi":
    serp = SerpApiFlightsClient(settings, cache)
    CASH_SOURCE_NAME = "serpapi google_flights"
else:
    serp = GoogleFlightsClient(cache, settings.cash_cache_minutes)
    CASH_SOURCE_NAME = GoogleFlightsClient.name

app = FastAPI(title="Waypoint")


@app.middleware("http")
async def password_gate(request: Request, call_next):
    """With APP_PASSWORD set, the whole app asks the browser for that password (any user name)."""
    if settings.app_password and request.url.path != "/healthz":
        given = ""
        header = request.headers.get("authorization", "")
        if header.lower().startswith("basic "):
            try:
                given = base64.b64decode(header[6:]).decode().partition(":")[2]
            except Exception:  # noqa: BLE001
                given = ""
        if not secrets.compare_digest(given.encode(), settings.app_password.encode()):
            return Response("Password required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Waypoint"'})
    return await call_next(request)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"ok": True}


def _airport(code: str) -> str:
    code = code.strip().upper()
    if not is_airport(code):
        raise HTTPException(422, f"Unknown airport code: {code}")
    return code


@app.get("/api/status")
def status() -> dict:
    return {
        "awards": {"source": "seats.aero", "rate_limit_remaining": seats.rate_limit_remaining},
        "cash": {"source": CASH_SOURCE_NAME, "configured": serp.configured},
    }


@app.get("/api/awards", response_model=AwardSearchResult)
async def awards(
    origin: str,
    destination: str,
    day: date = Query(alias="date"),
    flex: int = Query(1, ge=0, le=3),
) -> AwardSearchResult:
    try:
        return await search_awards(seats, _airport(origin), _airport(destination), day, flex)
    except SeatsAeroError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/awards/segments")
async def award_segments(availability_id: str, flights: str) -> dict:
    """Per-flight times and program booking links for one award leg (1 API call, cached)."""
    try:
        body = await seats.trip_details(availability_id)
    except SeatsAeroError as exc:
        raise HTTPException(502, str(exc)) from exc
    wanted = [f.strip() for f in flights.split(",") if f.strip()]
    for trip in body.get("data") or []:
        segs = sorted(trip.get("AvailabilitySegments") or [], key=lambda s: s.get("Order", 0))
        if [s.get("FlightNumber") for s in segs] == wanted:
            return {
                "segments": [
                    {
                        "flight_number": s.get("FlightNumber"),
                        "origin": s.get("OriginAirport"),
                        "destination": s.get("DestinationAirport"),
                        "departs_at": (s.get("DepartsAt") or "").rstrip("Z")[:19],
                        "arrives_at": (s.get("ArrivesAt") or "").rstrip("Z")[:19],
                        "duration_minutes": s.get("Duration") or 0,
                        "aircraft": s.get("AircraftName"),
                        "fare_class": s.get("FareClass"),
                    }
                    for s in segs
                ],
                "booking_links": [
                    {"label": b.get("label"), "link": b.get("link"), "primary": bool(b.get("primary"))}
                    for b in body.get("booking_links") or []
                    if str(b.get("link", "")).startswith("https://")
                ],
            }
    return {"segments": [], "booking_links": []}


_MAJOR = set(HUBS) | set(BEYOND_POOL)


@lru_cache(maxsize=1)
def _airport_index() -> list[dict]:
    rows = []
    for code, a in airportsdata.load("IATA").items():
        rows.append({"code": code, "city": a.get("city") or "", "name": a.get("name") or "", "country": a.get("country") or ""})
    return rows


@app.get("/api/airports")
def airports(q: str = Query(min_length=1, max_length=40)) -> list[dict]:
    needle = q.strip().lower()
    scored = []
    for a in _airport_index():
        code, city, name = a["code"].lower(), a["city"].lower(), a["name"].lower()
        if code == needle:
            rank = 0
        elif city.startswith(needle):
            rank = 1
        elif code.startswith(needle):
            rank = 2
        elif needle in name or needle in city:
            rank = 3
        else:
            continue
        # Prefer the big airports: first the known large ones, then "International" in the name.
        major = 0 if a["code"] in _MAJOR else 1 if "international" in name else 2
        scored.append((0 if rank == 0 else major, rank, len(a["city"]), a["city"], a["code"], a))
    return [a for *_, a in sorted(scored, key=lambda t: t[:5])[:8]]


@app.get("/api/airports/lookup")
def airport_lookup(codes: str = Query(max_length=2000)) -> dict:
    data = airportsdata.load("IATA")
    out = {}
    for code in {c.strip().upper() for c in codes.split(",")}:
        if code in data:
            out[code] = {"city": data[code].get("city") or code, "name": data[code].get("name") or code}
    return out


@app.get("/api/cash/all")
async def cash_all(origin: str, destination: str, day: date = Query(alias="date"), currency: str = "USD") -> dict:
    """Cash fares for all four cabins in one request (4 SerpApi searches, cached 30 min)."""
    if not serp.configured:
        raise HTTPException(503, "Cash fares are off: SERPAPI_KEY is not set.")
    o, d = _airport(origin), _airport(destination)
    cabins = list(TRAVEL_CLASS)
    results = await asyncio.gather(*(serp.one_way(o, d, day, c, currency.upper()) for c in cabins), return_exceptions=True)
    out: dict = {"cabins": {}, "errors": {}}
    for cabin, res in zip(cabins, results):
        if isinstance(res, Exception):
            out["errors"][cabin] = str(res)
        else:
            out["cabins"][cabin] = res.model_dump()
    return out


@app.get("/api/cash/roundtrip")
async def cash_roundtrip(
    origin: str, destination: str, day: date = Query(alias="date"), return_date: date = Query(), currency: str = "USD"
) -> dict:
    """Round-trip ticket prices for all four cabins (4 SerpApi searches, cached).

    Each itinerary is an outbound flight; its price is the round-trip total with the cheapest return.
    """
    if not serp.configured:
        raise HTTPException(503, "Cash fares are off: SERPAPI_KEY is not set.")
    if return_date < day:
        raise HTTPException(422, "return_date is before date")
    o, d = _airport(origin), _airport(destination)
    cabins = list(TRAVEL_CLASS)
    results = await asyncio.gather(
        *(serp.search(o, [d], day, c, currency.upper(), return_date=return_date) for c in cabins), return_exceptions=True
    )
    out: dict = {"cabins": {}, "errors": {}}
    for cabin, res in zip(cabins, results):
        if isinstance(res, Exception):
            out["errors"][cabin] = str(res)
        else:
            out["cabins"][cabin] = res.model_dump()
    return out


@app.get("/api/tricks", response_model=TrickResult)
async def tricks(
    origin: str,
    destination: str,
    day: date = Query(alias="date"),
    cabin: str = "business",
    currency: str = "USD",
    include_return: bool = True,
) -> TrickResult:
    """Return-ticket and hidden-city fares that beat the one-way fare (3 SerpApi searches, cached)."""
    if cabin not in TRAVEL_CLASS:
        raise HTTPException(422, f"cabin must be one of {list(TRAVEL_CLASS)}")
    if not serp.configured:
        raise HTTPException(503, "Fare tricks are off: SERPAPI_KEY is not set.")
    try:
        return await search_tricks(serp, _airport(origin), _airport(destination), day, cabin, currency.upper(), include_return)
    except SerpApiError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/transfers")
def transfers() -> dict:
    data = json.loads((Path(__file__).parent / "data" / "transfers.json").read_text())
    return {
        "currencies": data["currencies"],
        "programs": [{"id": k, "name": v.name, "alliance": v.alliance} for k, v in sorted(PROGRAMS.items(), key=lambda kv: kv[1].name)],
    }


@app.get("/api/cash", response_model=CashSearchResult)
async def cash(
    origin: str,
    destination: str,
    day: date = Query(alias="date"),
    cabin: str = "economy",
    currency: str = "USD",
) -> CashSearchResult:
    if cabin not in TRAVEL_CLASS:
        raise HTTPException(422, f"cabin must be one of {list(TRAVEL_CLASS)}")
    if not serp.configured:
        raise HTTPException(503, "Cash fares are off: SERPAPI_KEY is not set.")
    try:
        return await serp.one_way(_airport(origin), _airport(destination), day, cabin, currency.upper())
    except SerpApiError as exc:
        raise HTTPException(502, str(exc)) from exc


# The built web UI (frontend/ -> static/) is served from the same app.
if settings.static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=settings.static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        root = settings.static_dir.resolve()
        target = (root / path).resolve()
        if path and target.is_relative_to(root) and target.is_file():
            return FileResponse(target)
        return FileResponse(settings.static_dir / "index.html")
