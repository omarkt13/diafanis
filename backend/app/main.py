from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.cache import Cache
from app.config import load_settings
from app.engine.awards import AwardSearchResult, search_awards
from app.engine.geo import is_airport
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


@app.get("/api/awards/trip/{availability_id}")
async def award_trip(availability_id: str) -> dict:
    try:
        return await seats.trip_details(availability_id)
    except SeatsAeroError as exc:
        raise HTTPException(502, str(exc)) from exc


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
