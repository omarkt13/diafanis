from datetime import date

from app.engine.tricks import find_hidden_city, find_return_tricks, pick_beyond, search_tricks
from app.sources.serpapi_flights import CashItinerary, CashSearchResult, CashSegment

D = "2026-11-20T"


def seg(fn, o, d, dep, arr, dur=120):
    return CashSegment(flight_number=fn, airline=fn[:2], origin=o, destination=d, departs_at=D + dep, arrives_at=D + arr,
                       duration_minutes=dur, aircraft=None, travel_class=None)


def it(price, *segs):
    return CashItinerary(price=price, currency="USD", departs_at=segs[0].departs_at, arrives_at=segs[-1].arrives_at,
                         duration_minutes=sum(s.duration_minutes for s in segs), stops=len(segs) - 1,
                         via=[s.destination for s in segs[:-1]], airlines=[], segments=list(segs), best=False, booking_token=None)


def res(*its, cabin="business"):
    return CashSearchResult(origin="RUH", destination="GVA", date="2026-11-20", cabin=cabin, currency="USD",
                            itineraries=list(its), lowest_price=None, price_level=None, typical_range=None)


SV = (seg("SV 1017", "RUH", "JED", "05:00", "06:50"), seg("SV 237", "JED", "GVA", "09:00", "13:35", 395))
LX = (seg("LX 243", "RUH", "ZRH", "02:00", "06:30", 390), seg("LX 2802", "ZRH", "GVA", "07:30", "08:20", 50))


def test_return_ticket_cheaper_than_one_way_on_same_flights():
    one_way = res(it(3336, *SV), it(2900, *LX))
    rt = res(it(2100, *SV), it(5200, *LX))
    tricks = find_return_tricks(one_way, [("2026-11-27", rt)])
    assert len(tricks) == 1
    t = tricks[0]
    assert (t.kind, t.price, t.normal_price, t.saving, t.same_flights, t.return_date) == ("return", 2100, 3336, 1236, True, "2026-11-27")


def test_return_ticket_keeps_cheapest_return_date_and_ignores_small_savings():
    one_way = res(it(1000, *SV))
    tricks = find_return_tricks(one_way, [("2026-11-27", res(it(800, *SV))), ("2026-12-04", res(it(700, *SV))),
                                          ("2026-12-11", res(it(980, *LX)))])
    assert [(t.price, t.return_date) for t in tricks] == [(700, "2026-12-04")]


def test_hidden_city_cuts_the_trip_at_the_destination():
    one_way = res(it(2900, *LX))
    onward = seg("LX 352", "GVA", "LHR", "10:00", "10:45", 105)
    beyond = res(it(1800, *LX, onward), it(1700, seg("BA 262", "RUH", "LHR", "01:00", "06:00", 420)),
                 it(2890, *LX, seg("LX 350", "GVA", "LHR", "12:00", "12:45", 105)))
    tricks = find_hidden_city(one_way, beyond, "GVA")
    assert len(tricks) == 1
    t = tricks[0]
    assert (t.kind, t.price, t.saving, t.ticketed_to, t.same_flights) == ("hidden", 1800, 1100, "LHR", True)
    assert [s.destination for s in t.itinerary.segments] == ["ZRH", "GVA"]
    assert [s.flight_number for s in t.dropped] == ["LX 352"]
    assert t.itinerary.duration_minutes == 390 + 60 + 50  # two flights and a 60 min layover


def test_hidden_city_ignores_trips_that_end_at_the_destination_or_cost_more():
    one_way = res(it(1000, *LX))
    beyond = res(it(1500, *LX, seg("LX 352", "GVA", "LHR", "10:00", "10:45")))
    assert find_hidden_city(one_way, beyond, "GVA") == []


def test_pick_beyond_gives_nearby_large_airports():
    b = pick_beyond("RUH", "GVA")
    assert "GVA" not in b and "RUH" not in b and 1 <= len(b) <= 7
    assert {"CDG", "FRA"} & set(b)


class FakeSerp:
    def __init__(self):
        self.calls_made = 0
        self.seen = []

    async def one_way(self, o, d, day, cabin, currency):
        return await self.search(o, [d], day, cabin, currency)

    async def search(self, o, dests, day, cabin, currency, return_date=None):
        self.calls_made += 1
        self.seen.append((tuple(dests), return_date))
        if return_date:
            return res(it(2100, *SV))
        if len(dests) > 1:
            return res(it(1800, *LX, seg("LX 352", "GVA", "LHR", "10:00", "10:45")))
        return res(it(3336, *SV), it(2900, *LX))


async def test_search_tricks_uses_four_calls_and_finds_both_kinds():
    serp = FakeSerp()
    r = await search_tricks(serp, "RUH", "GVA", date(2026, 11, 20), "business")
    assert r.api_calls == 4  # one-way (cached in real use), two return dates, one beyond search
    assert sorted(t.kind for t in r.tricks) == ["hidden", "return"]
    assert serp.seen[1][1] == date(2026, 11, 27) and serp.seen[2][1] == date(2026, 12, 4)
