from __future__ import annotations

import asyncio
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import airportsdata

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.cache import Cache
from app.config import load_settings
from app.engine.awards import AwardSearchResult, search_awards
from app.engine.geo import is_airport
from app.engine.programs import PROGRAMS
from app.engine.tricks import TrickResult, search_tricks
from app.sources.seats_aero import SeatsAeroClient, SeatsAeroError
from app.sources.serpapi_flights import TRAVEL_CLASS, CashSearchResult, SerpApiError, SerpApiFlightsClient

settings = load_settings()
cache = Cache(settings.cache_path)
seats = SeatsAeroClient(settings, cache)
serp = SerpApiFlightsClient(settings, cache)

app = FastAPI(title="Travel tool")


def _airport(code: str) -> str:
    code = code.strip().upper()
    if not is_airport(code):
        raise HTTPException(422, f"Unknown airport code: {code}")
    return code


@app.get("/api/status")
def status() -> dict:
    return {
        "awards": {"source": "seats.aero", "rate_limit_remaining": seats.rate_limit_remaining},
        "cash": {"source": "serpapi google_flights", "configured": serp.configured},
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
        # Prefer the big airports of a city: "International" in the name is a fair signal.
        scored.append((rank, 0 if "international" in name else 1, a["city"], a))
    return [a for *_, a in sorted(scored, key=lambda t: t[:3])[:8]]


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


@app.get("/api/tricks", response_model=TrickResult)
async def tricks(
    origin: str,
    destination: str,
    day: date = Query(alias="date"),
    cabin: str = "business",
    currency: str = "USD",
) -> TrickResult:
    """Return-ticket and hidden-city fares that beat the one-way fare (3 SerpApi searches, cached)."""
    if cabin not in TRAVEL_CLASS:
        raise HTTPException(422, f"cabin must be one of {list(TRAVEL_CLASS)}")
    if not serp.configured:
        raise HTTPException(503, "Fare tricks are off: SERPAPI_KEY is not set.")
    try:
        return await search_tricks(serp, _airport(origin), _airport(destination), day, cabin, currency.upper())
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
