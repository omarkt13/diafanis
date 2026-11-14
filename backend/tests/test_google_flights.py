# Fixtures are real Google Flights page data for DXB-GVA business, 2026-11-27
# (round trip: back on 2026-12-04), cut down to the parts the parser reads.
import json
from datetime import date
from pathlib import Path

import pytest

from app.cache import Cache
from app.sources import google_flights as gf
from app.sources.serpapi_flights import CashItinerary, CashSegment

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def test_parse_page_one_way():
    its, ins = gf.parse_page(load("google_page_one_way.json"), "business", "USD")
    by = {tuple(s.flight_number for s in i.segments): i for i in its}
    assert len(its) == 9 and sum(i.best for i in its) == 3
    assert by[("MS 911", "MS 771")].price == 1072 and by[("TK 761", "TK 1921")].price == 2893 and by[("EK 89",)].price == 4780
    ek = by[("EK 83",)]
    assert (ek.departs_at, ek.arrives_at, ek.duration_minutes, ek.stops) == ("2026-11-27T14:40", "2026-11-27T18:45", 425, 0)
    rj = by[("RJ 615", "RJ 155")]
    assert rj.via == ["AMM"] and rj.arrives_at == "2026-11-28T13:55" and rj.segments[0].arrives_at == "2026-11-28T01:20"
    assert rj.segments[0].travel_class == "Business" and rj.segments[0].airline == "Royal Jordanian" and rj.other_cabin == []
    assert ins == {"typical_range": [1300.0, 1500.0], "price_level": "low", "lowest_price": 1072.0}


def test_parse_page_round_trip_prices_are_totals():
    its, ins = gf.parse_page(load("google_page_round_trip.json"), "business", "USD")
    by = {tuple(s.flight_number for s in i.segments): i.price for i in its}
    assert by[("MS 911", "MS 771")] == 1590  # 1072 one way
    assert ins["lowest_price"] == 1590


def test_parse_page_marks_flights_in_another_cabin_and_survives_bad_rows():
    page = load("google_page_one_way.json")
    its, _ = gf.parse_page(page, "premium", "USD")
    assert its == []  # every flight is business: none is in the premium cabin
    page[3][0].append(["broken"])
    assert len(gf.parse_page(page, "business", "USD")[0]) == 9
    assert gf.parse_page([None] * 6, "business", "USD") == ([], {})


def seg(fn):
    return CashSegment(flight_number=fn, airline="X", origin="A", destination="B", departs_at="2026-11-27T10:00",
                       arrives_at="2026-11-27T12:00", duration_minutes=120, aircraft=None, travel_class=None)


def it(price, *fns, best=False):
    return CashItinerary(price=price, currency="USD", departs_at="2026-11-27T10:00", arrives_at="2026-11-27T12:00", duration_minutes=120,
                         stops=len(fns) - 1, via=[], airlines=["X"], segments=[seg(f) for f in fns], best=best, booking_token=None)


def test_merge_keeps_one_entry_for_each_set_of_flights():
    merged = gf.merge([it(500, "TK 1", best=True)], [it(480, "TK 1"), it(300, "MS 2")])
    assert [(i.price, i.best, i.segments[0].flight_number) for i in merged] == [(480, True, "TK 1"), (300, False, "MS 2")]


async def test_client_uses_cache_and_falls_back_when_one_request_fails(monkeypatch):
    calls = []

    def page(origin, dest, day, cabin, currency, ret):
        calls.append("page")
        return load("google_page_one_way.json")

    def full(origin, dests, day, cabin, currency):
        calls.append("full")
        raise RuntimeError("blocked")

    monkeypatch.setattr(gf, "_fetch_page", page)
    monkeypatch.setattr(gf, "_fetch_full", full)
    client = gf.GoogleFlightsClient(Cache(":memory:"))
    r = await client.one_way("dxb", "gva", date(2026, 11, 27), "business", "USD")
    assert len(r.itineraries) == 9 and r.lowest_price == 1072 and r.price_level == "low"
    await client.one_way("DXB", "GVA", date(2026, 11, 27), "business", "USD")
    assert sorted(calls) == ["full", "page"]  # the second search came from the cache

    monkeypatch.setattr(gf, "_fetch_page", lambda *a: (_ for _ in ()).throw(RuntimeError("blocked")))
    with pytest.raises(gf.GoogleFlightsError):
        await client.one_way("DXB", "ZRH", date(2026, 11, 27), "business", "USD")


async def test_round_trip_and_multi_destination_use_one_request_each(monkeypatch):
    calls = []
    monkeypatch.setattr(gf, "_fetch_page", lambda *a: calls.append(("page", a[1], a[5])) or load("google_page_round_trip.json"))
    monkeypatch.setattr(gf, "_fetch_full", lambda *a: calls.append(("full", tuple(a[1]))) or [it(700, "EK 1", "LX 2")])
    client = gf.GoogleFlightsClient(Cache(":memory:"))
    await client.search("DXB", ["GVA"], date(2026, 11, 27), "business", "USD", return_date=date(2026, 12, 4))
    r = await client.search("DXB", ["MXP", "ZRH"], date(2026, 11, 27), "business", "USD")
    assert calls == [("page", "GVA", date(2026, 12, 4)), ("full", ("MXP", "ZRH"))]
    assert r.destination == "MXP,ZRH" and r.itineraries[0].price == 700
