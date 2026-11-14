from __future__ import annotations

import math
from functools import lru_cache

import airportsdata


@lru_cache(maxsize=1)
def _airports() -> dict:
    return airportsdata.load("IATA")


def is_airport(code: str) -> bool:
    return code.upper() in _airports()


def distance_km(a: str, b: str) -> float:
    ap = _airports()
    p, q = ap[a.upper()], ap[b.upper()]
    lat1, lon1, lat2, lon2 = map(math.radians, (p["lat"], p["lon"], q["lat"], q["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# Connection hubs the engine may route through when it joins two award legs.
# Seats.aero stores award seats per airport pair and does not join flights
# itself, so a Turkish award DXB-IST-GVA only shows up as two legs.
HUBS = [
    "IST", "DOH", "DXB", "AUH", "CAI", "AMM", "BAH", "JED", "RUH", "ADD",
    "FRA", "MUC", "ZRH", "VIE", "LHR", "CDG", "AMS", "FCO", "MAD", "LIS",
    "ATH", "WAW", "CPH", "BRU", "HEL", "DUB",
    "SIN", "HKG", "BKK", "ICN", "NRT", "HND", "TPE", "KUL", "DEL", "BOM",
    "JFK", "EWR", "ORD", "IAD", "YYZ", "YUL", "LAX", "SFO", "DFW", "ATL",
]


def pick_hubs(origin: str, destination: str, max_detour: float = 1.5, limit: int = 15) -> list[str]:
    """Hubs whose detour (O-H + H-D over O-D) is below max_detour, best first."""
    direct = distance_km(origin, destination)
    if direct <= 0:
        return []
    scored = []
    for hub in HUBS:
        if hub in (origin.upper(), destination.upper()) or not is_airport(hub):
            continue
        ratio = (distance_km(origin, hub) + distance_km(hub, destination)) / direct
        if ratio <= max_detour:
            scored.append((ratio, hub))
    return [hub for _, hub in sorted(scored)[:limit]]
