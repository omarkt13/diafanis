from datetime import date, datetime, timezone

import pytest

from app.cache import Cache
from app.engine.awards import build_options, parse_leg, search_awards
from app.engine.geo import pick_hubs

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def trip(src, cabin, origin, dest, dep, arr, flights, miles, taxes=10000, cur="CAD", seats=4, conns=None, dur=300,
         updated="2026-11-14T00:00:00Z", aid=None):
    return {
        "AvailabilityID": aid or f"{src}-{origin}-{dest}-{dep}",
        "Source": src, "Cabin": cabin, "OriginAirport": origin, "DestinationAirport": dest,
        "DepartsAt": dep + ":00Z", "ArrivesAt": arr + ":00Z", "FlightNumbers": flights,
        "MileageCost": miles, "TotalTaxes": taxes, "TaxesCurrency": cur, "RemainingSeats": seats,
        "Connections": conns or [], "TotalDuration": dur, "Carriers": flights[:2],
        "Aircraft": ["Boeing 737-800"], "FareClasses": ["I"], "UpdatedAt": updated,
    }


def row(src, *trips):
    return {"Source": src, "AvailabilityTrips": list(trips)}


def test_parse_leg_reads_local_times_and_minor_unit_taxes():
    leg = parse_leg(trip("aeroplan", "business", "DXB", "IST", "2026-11-20T09:30", "2026-11-20T13:20",
                         "TK759", 30000, taxes=12345, seats=0))
    assert leg.departs_at == "2026-11-20T09:30:00"
    assert leg.taxes == 123.45
    assert leg.seats is None  # 0 means the program did not report a count
    assert leg.flight_numbers == ["TK759"]


def test_joins_two_legs_of_the_same_program_and_cabin():
    out = [row("aeroplan", trip("aeroplan", "business", "DXB", "IST", "2026-11-20T09:30", "2026-11-20T13:20", "TK759", 30000, seats=2))]
    inn = [row("aeroplan", trip("aeroplan", "business", "IST", "GVA", "2026-11-20T15:30", "2026-11-20T17:10", "TK1919", 22500, seats=6))]
    opts = build_options([], out, inn, "DXB", "GVA", NOW)
    assert len(opts) == 1
    o = opts[0]
    assert (o.kind, o.program, o.cabin, o.miles, o.via, o.seats) == ("joined", "aeroplan", "business", 52500, ["IST"], 2)
    assert o.taxes == 200.0 and o.taxes_currency == "CAD"
    # 09:30 Dubai (UTC+4) to 17:10 Geneva (UTC+1) is 10h40.
    assert o.duration_minutes == 640


@pytest.mark.parametrize(
    "dep2, joined",
    [("2026-11-20T13:50", False),  # 30 min connection: too short
     ("2026-11-20T14:20", True),   # 60 min: allowed
     ("2026-11-21T14:00", False)], # 24h40: too long
)
def test_connection_time_window(dep2, joined):
    out = [row("united", trip("united", "economy", "DXB", "IST", "2026-11-20T09:30", "2026-11-20T13:20", "TK759", 20000))]
    inn = [row("united", trip("united", "economy", "IST", "GVA", dep2, dep2[:11] + "23:00", "TK1919", 15000))]
    assert bool(build_options([], out, inn, "DXB", "GVA", NOW)) is joined


def test_does_not_join_different_programs_or_cabins():
    out = [row("aeroplan", trip("aeroplan", "business", "DXB", "IST", "2026-11-20T09:30", "2026-11-20T13:20", "TK759", 30000))]
    inn = [row("united", trip("united", "business", "IST", "GVA", "2026-11-20T15:30", "2026-11-20T17:10", "TK1919", 22500)),
           row("aeroplan", trip("aeroplan", "economy", "IST", "GVA", "2026-11-20T15:30", "2026-11-20T17:10", "TK1919", 15000))]
    assert build_options([], out, inn, "DXB", "GVA", NOW) == []


def test_drops_paths_that_repeat_an_airport():
    out = [row("delta", trip("delta", "business", "DXB", "CDG", "2026-11-20T01:30", "2026-11-20T09:00", "AF655, AF1234", 40000, conns=["FCO"]))]
    inn = [row("delta", trip("delta", "business", "CDG", "GVA", "2026-11-20T12:00", "2026-11-20T19:00", "AF1, AF2", 20000, conns=["FCO"]))]
    assert build_options([], out, inn, "DXB", "GVA", NOW) == []


def test_keeps_cheapest_copy_of_the_same_flights():
    a = trip("emirates", "business", "DXB", "GVA", "2026-11-20T14:40", "2026-11-20T18:45", "EK89", 100000, aid="a")
    b = trip("emirates", "business", "DXB", "GVA", "2026-11-20T14:40", "2026-11-20T18:45", "EK89", 59000, aid="b")
    opts = build_options([row("emirates", a), row("emirates", b)], [], [], "DXB", "GVA", NOW)
    assert [o.miles for o in opts] == [59000]


def test_data_age_uses_the_oldest_leg():
    out = [row("aeroplan", trip("aeroplan", "economy", "DXB", "IST", "2026-11-20T09:30", "2026-11-20T13:20", "TK759", 15000,
                                updated="2026-11-04T12:00:00Z"))]
    inn = [row("aeroplan", trip("aeroplan", "economy", "IST", "GVA", "2026-11-20T15:30", "2026-11-20T17:10", "TK1919", 15000,
                                updated="2026-11-14T06:00:00Z"))]
    assert build_options([], out, inn, "DXB", "GVA", NOW)[0].data_age_hours == 240.0


def test_pick_hubs_keeps_on_the_way_airports():
    hubs = pick_hubs("DXB", "GVA")
    assert "IST" in hubs and "DOH" in hubs
    assert "SIN" not in hubs and "JFK" not in hubs


class FakeSeats:
    def __init__(self):
        self.calls = []
        self.calls_made = 0
        self.rate_limit_remaining = 900

    async def search(self, origins, destinations, start, end, sources=None):
        self.calls.append((tuple(origins), tuple(destinations), start, end))
        self.calls_made += 1
        if origins == ["DXB"] and destinations == ["GVA"]:
            return [row("emirates", trip("emirates", "business", "DXB", "GVA", "2026-11-20T14:40", "2026-11-20T18:45", "EK89", 59000))]
        return []


async def test_search_uses_three_calls_and_filters_dates():
    client = FakeSeats()
    res = await search_awards(client, "dxb", "gva", date(2026, 11, 20), flex_days=1)
    assert res.api_calls == 3
    assert res.dates == ["2026-11-19", "2026-11-20", "2026-11-21"]
    assert [o.program for o in res.options] == ["emirates"]
    inbound = client.calls[2]
    assert inbound[1] == ("GVA",) and inbound[3] == date(2026, 11, 22)  # inbound legs may land a day later


def test_cache_round_trip_and_expiry():
    c = Cache(":memory:")
    c.set("k", {"a": 1}, 60)
    assert c.get("k") == {"a": 1}
    c.set("old", [1], -1)
    assert c.get("old") is None


def test_same_times_and_stops_show_as_one_row_and_carriers_are_not_repeated():
    def pair(n, miles):
        out = row("delta", {**trip("delta", "business", "DXB", "CDG", "2026-11-20T01:30", "2026-11-20T06:00", f"AF{n}", miles, aid=f"o{n}"), "Carriers": "AF, AF"})
        inn = row("delta", trip("delta", "business", "CDG", "GVA", "2026-11-20T08:00", "2026-11-20T09:10", f"AF{n + 1}", 10000, aid=f"i{n}"))
        return out, inn
    (o1, i1), (o2, i2) = pair(100, 60000), pair(200, 50000)
    opts = build_options([], [o1, o2], [i1, i2], "DXB", "GVA", NOW)
    assert [(o.miles, o.carriers) for o in opts] == [(60000, ["AF"])]
