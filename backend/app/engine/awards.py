from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import airportsdata
from pydantic import BaseModel

from app.engine.geo import pick_hubs
from app.engine.programs import program
from app.sources.seats_aero import SeatsAeroClient

Cabin = Literal["economy", "premium", "business", "first"]
CABIN_ORDER: dict[str, int] = {"economy": 0, "premium": 1, "business": 2, "first": 3}

MIN_CONNECT_MIN = 60
MAX_CONNECT_MIN = 24 * 60
MAX_JOINED_PER_GROUP = 4
MAX_JOINED_DURATION_MIN = 30 * 60

_TZ = airportsdata.load("IATA")


class Leg(BaseModel):
    availability_id: str
    flight_numbers: list[str]
    origin: str
    destination: str
    connections: list[str]
    departs_at: str  # local time at origin, ISO, no zone
    arrives_at: str  # local time at destination
    duration_minutes: int
    carriers: list[str]
    aircraft: list[str]
    fare_classes: list[str]
    miles: int
    taxes: float
    taxes_currency: str | None
    seats: int | None  # None: the program did not say
    updated_at: str


class AwardOption(BaseModel):
    id: str
    kind: Literal["direct", "joined"]
    program: str
    program_name: str
    alliance: str | None
    book_url: str
    cabin: Cabin
    origin: str
    destination: str
    departs_at: str
    arrives_at: str
    duration_minutes: int
    stops: int
    via: list[str]
    carriers: list[str]
    miles: int
    taxes: float
    taxes_currency: str | None
    seats: int | None
    data_age_hours: float
    legs: list[Leg]
    note: str | None = None


class AwardSearchResult(BaseModel):
    origin: str
    destination: str
    dates: list[str]
    hubs: list[str]
    options: list[AwardOption]
    api_calls: int
    rate_limit_remaining: int | None


def _split(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [p.strip() for p in str(value).split(",") if p.strip()]


def _local(ts: str) -> str:
    # Seats.aero marks flight times with "Z" but they are local airport times.
    return ts.rstrip("Z")[:19]


def parse_leg(trip: dict[str, Any]) -> Leg:
    seats = trip.get("RemainingSeats") or None
    return Leg(
        availability_id=str(trip.get("AvailabilityID") or trip.get("ID")),
        flight_numbers=_split(trip.get("FlightNumbers")),
        origin=trip["OriginAirport"],
        destination=trip["DestinationAirport"],
        connections=_split(trip.get("Connections")),
        departs_at=_local(trip["DepartsAt"]),
        arrives_at=_local(trip["ArrivesAt"]),
        duration_minutes=int(trip.get("TotalDuration") or 0),
        carriers=_split(trip.get("Carriers")),
        aircraft=_split(trip.get("Aircraft")),
        fare_classes=_split(trip.get("FareClasses")),
        miles=int(trip.get("MileageCost") or 0),
        taxes=round((trip.get("TotalTaxes") or 0) / 100, 2),
        taxes_currency=trip.get("TaxesCurrency") or None,
        seats=int(seats) if seats else None,
        updated_at=trip.get("UpdatedAt") or "",
    )


def _trips(rows: list[dict[str, Any]]) -> list[tuple[str, Leg]]:
    out = []
    for row in rows:
        for trip in row.get("AvailabilityTrips") or []:
            cabin = trip.get("Cabin")
            if cabin in CABIN_ORDER and trip.get("MileageCost"):
                out.append((cabin, parse_leg(trip)))
    return out


def _utc(local_iso: str, airport: str) -> datetime:
    tz = ZoneInfo(_TZ[airport]["tz"]) if airport in _TZ else timezone.utc
    return datetime.fromisoformat(local_iso).replace(tzinfo=tz).astimezone(timezone.utc)


def _age_hours(updated: list[str], now: datetime) -> float:
    stamps = [datetime.fromisoformat(u.replace("Z", "+00:00")) for u in updated if u]
    if not stamps:
        return -1.0
    return round((now - min(stamps)).total_seconds() / 3600, 1)


def _option(kind: str, src: str, cabin: str, legs: list[Leg], now: datetime, note: str | None = None) -> AwardOption:
    first, last = legs[0], legs[-1]
    prog = program(src)
    via: list[str] = []
    for i, leg in enumerate(legs):
        via += leg.connections
        if i < len(legs) - 1:
            via.append(leg.destination)
    total = _utc(last.arrives_at, last.destination) - _utc(first.departs_at, first.origin)
    currencies = {leg.taxes_currency for leg in legs if leg.taxes}
    seat_counts = [leg.seats for leg in legs if leg.seats]
    carriers: list[str] = []
    for leg in legs:
        carriers += [c for c in leg.carriers if c not in carriers]
    return AwardOption(
        id=f"{src}:{cabin}:" + "+".join(leg.availability_id + "/" + "-".join(leg.flight_numbers) for leg in legs),
        kind=kind,  # type: ignore[arg-type]
        program=src,
        program_name=prog.name,
        alliance=prog.alliance,
        book_url=prog.url,
        cabin=cabin,  # type: ignore[arg-type]
        origin=first.origin,
        destination=last.destination,
        departs_at=first.departs_at,
        arrives_at=last.arrives_at,
        duration_minutes=int(total.total_seconds() // 60),
        stops=len(via),
        via=via,
        carriers=carriers,
        miles=sum(leg.miles for leg in legs),
        taxes=round(sum(leg.taxes for leg in legs), 2),
        taxes_currency=next(iter(currencies)) if len(currencies) == 1 else (None if not currencies else "mixed"),
        seats=min(seat_counts) if len(seat_counts) == len(legs) else None,
        data_age_hours=_age_hours([leg.updated_at for leg in legs], now),
        legs=legs,
        note=note,
    )


JOINED_NOTE = (
    "Joined from two award legs. Miles are the sum of the legs; the program can price the "
    "whole trip from its own chart, often lower. Book both flights as one award."
)


def build_options(
    direct_rows: list[dict[str, Any]],
    out_rows: list[dict[str, Any]],
    in_rows: list[dict[str, Any]],
    origin: str,
    destination: str,
    now: datetime | None = None,
) -> list[AwardOption]:
    now = now or datetime.now(timezone.utc)
    options: dict[str, AwardOption] = {}

    for row in direct_rows:
        src = row.get("Source") or row.get("Route", {}).get("Source")
        for cabin, leg in _trips([row]):
            opt = _option("direct", src, cabin, [leg], now)
            options.setdefault(opt.id, opt)
    direct_flights = {(o.program, o.cabin, tuple(o.legs[0].flight_numbers)) for o in options.values()}

    # Index inbound legs (hub -> destination) by program, cabin and hub.
    inbound: dict[tuple[str, str, str], list[Leg]] = defaultdict(list)
    for row in in_rows:
        src = row.get("Source")
        for cabin, leg in _trips([row]):
            if origin not in leg.connections:
                inbound[(src, cabin, leg.origin)].append(leg)

    groups: dict[tuple[str, str, str], list[AwardOption]] = defaultdict(list)
    for row in out_rows:
        src = row.get("Source")
        for cabin, first in _trips([row]):
            if destination in first.connections:
                continue
            for second in inbound.get((src, cabin, first.destination), []):
                gap = datetime.fromisoformat(second.departs_at) - datetime.fromisoformat(first.arrives_at)
                if not timedelta(minutes=MIN_CONNECT_MIN) <= gap <= timedelta(minutes=MAX_CONNECT_MIN):
                    continue
                flights = tuple(first.flight_numbers + second.flight_numbers)
                if (src, cabin, flights) in direct_flights:
                    continue
                opt = _option("joined", src, cabin, [first, second], now, JOINED_NOTE)
                path = [origin, *opt.via, destination]
                if len(set(path)) != len(path) or opt.duration_minutes > MAX_JOINED_DURATION_MIN:
                    continue
                groups[(src, cabin, first.departs_at[:10])].append(opt)

    for group in groups.values():
        group.sort(key=lambda o: (o.miles, o.duration_minutes))
        for opt in group[:MAX_JOINED_PER_GROUP]:
            options.setdefault(opt.id, opt)

    # The same flights can come back under several availability rows: keep the cheapest.
    best: dict[tuple, AwardOption] = {}
    for opt in options.values():
        key = (opt.program, opt.cabin, tuple(f for leg in opt.legs for f in leg.flight_numbers), opt.departs_at)
        if key not in best or (opt.miles, opt.taxes) < (best[key].miles, best[key].taxes):
            best[key] = opt
    return sorted(best.values(), key=lambda o: (o.departs_at[:10], -CABIN_ORDER[o.cabin], o.miles))


async def search_awards(
    client: SeatsAeroClient, origin: str, destination: str, day: date, flex_days: int = 1
) -> AwardSearchResult:
    origin, destination = origin.upper(), destination.upper()
    start, end = day - timedelta(days=flex_days), day + timedelta(days=flex_days)
    hubs = pick_hubs(origin, destination)
    calls_before = client.calls_made

    direct, out_legs, in_legs = await asyncio.gather(
        client.search([origin], [destination], start, end),
        client.search([origin], hubs, start, end) if hubs else _empty(),
        client.search(hubs, [destination], start, end + timedelta(days=1)) if hubs else _empty(),
    )
    options = build_options(direct, out_legs, in_legs, origin, destination)
    options = [o for o in options if start.isoformat() <= o.departs_at[:10] <= end.isoformat()]
    return AwardSearchResult(
        origin=origin,
        destination=destination,
        dates=[(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)],
        hubs=hubs,
        options=options,
        api_calls=client.calls_made - calls_before,
        rate_limit_remaining=client.rate_limit_remaining,
    )


async def _empty() -> list[dict[str, Any]]:
    return []
