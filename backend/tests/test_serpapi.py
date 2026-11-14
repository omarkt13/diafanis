# The sample follows the SerpApi Google Flights documentation. It is not a
# recorded live response yet: replace it with one after the first live call.
from app.sources.serpapi_flights import normalize

SAMPLE = {
    "best_flights": [
        {
            "flights": [
                {"departure_airport": {"id": "DXB", "time": "2026-11-20 09:30"},
                 "arrival_airport": {"id": "IST", "time": "2026-11-20 13:20"},
                 "duration": 290, "airplane": "Boeing 777", "airline": "Turkish Airlines",
                 "travel_class": "Business", "flight_number": "TK 759"},
                {"departure_airport": {"id": "IST", "time": "2026-11-20 15:30"},
                 "arrival_airport": {"id": "GVA", "time": "2026-11-20 17:10"},
                 "duration": 220, "airline": "Turkish Airlines", "travel_class": "Business",
                 "flight_number": "TK 1919"},
            ],
            "layovers": [{"id": "IST", "duration": 130}],
            "total_duration": 640,
            "price": 2896,
            "booking_token": "tok",
        }
    ],
    "other_flights": [
        {"flights": [{"departure_airport": {"id": "DXB", "time": "2026-11-20 14:40"},
                      "arrival_airport": {"id": "GVA", "time": "2026-11-20 18:45"},
                      "duration": 425, "airline": "Emirates", "flight_number": "EK 89"}],
         "total_duration": 425, "price": 4100},
        {"flights": [], "price": 1},
    ],
    "price_insights": {"lowest_price": 2209, "price_level": "typical", "typical_price_range": [2000, 3500]},
}


def test_normalize_reads_itineraries_and_insights():
    res = normalize(SAMPLE, "DXB", "GVA", "2026-11-20", "business", "USD")
    assert len(res.itineraries) == 2
    first = res.itineraries[0]
    assert first.best and first.price == 2896 and first.via == ["IST"] and first.stops == 1
    assert first.airlines == ["Turkish Airlines"]
    assert first.departs_at == "2026-11-20T09:30" and first.arrives_at == "2026-11-20T17:10"
    assert first.booking_token == "tok"
    assert res.itineraries[1].stops == 0 and not res.itineraries[1].best
    assert (res.lowest_price, res.price_level, res.typical_range) == (2209, "typical", [2000, 3500])


# A live response for DXB-GVA business on 2026-11-27 (show_hidden=true), saved by scripts/smoke.py.
def _live():
    import json
    from pathlib import Path

    body = json.loads((Path(__file__).parent / "fixtures" / "serpapi_one_way.json").read_text())
    return body, normalize(body, "DXB", "GVA", "2026-11-27", "business", "USD")


def test_live_fixture_holds_no_key_or_search_metadata():
    body, _ = _live()
    assert "search_metadata" not in body and "search_parameters" not in body
    assert "api_key" not in str(body)


def test_live_fixture_normalizes():
    body, res = _live()
    raw = (body.get("best_flights") or []) + (body.get("other_flights") or [])
    assert len(res.itineraries) == len(raw) == 69
    assert res.lowest_price == 1072 and res.price_level == "low" and res.typical_range == [1300, 1500]
    for it in res.itineraries:
        assert it.price and it.price > 0
        assert it.segments[0].origin == "DXB" and it.segments[-1].destination == "GVA"
        assert it.stops == len(it.segments) - 1 == len(it.via)
        assert it.booking_token
        assert it.duration_minutes >= sum(s.duration_minutes for s in it.segments)
        for s in it.segments:
            assert len(s.departs_at) == 16 and s.departs_at[10] == "T" and len(s.arrives_at) == 16
            code, _, number = s.flight_number.partition(" ")
            assert len(code) == 2 and number.isdigit()
            assert s.airline and s.travel_class


def test_live_fixture_has_the_turkish_fare_from_the_full_list():
    _, res = _live()
    by_flights = {tuple(s.flight_number for s in it.segments): it.price for it in res.itineraries}
    assert by_flights[("EK 89",)] == 4780
    # Google's short list has only TK 759 + TK 1919 at 5063. The lower fare is in the full list.
    assert by_flights[("TK 761", "TK 1921")] == 2893


def test_search_asks_for_the_full_list():
    import asyncio
    from datetime import date

    import httpx

    from app.cache import Cache
    from app.config import Settings
    from app.sources.serpapi_flights import SerpApiFlightsClient

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=SAMPLE)

    settings = Settings(seats_aero_key=None, serpapi_key="k", cache_path=":memory:", static_dir=None)
    client = SerpApiFlightsClient(settings, Cache(":memory:"), httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    asyncio.run(client.search("DXB", ["GVA"], date(2026, 11, 27), "business", "USD", return_date=date(2026, 12, 4)))
    assert seen["show_hidden"] == "true" and seen["type"] == "1" and seen["return_date"] == "2026-12-04"


def test_fares_in_another_cabin_are_marked_or_dropped():
    def flight(number, cls):
        return {"departure_airport": {"id": "DXB", "time": "2026-11-27 01:30"}, "arrival_airport": {"id": "GVA", "time": "2026-11-27 09:40"},
                "duration": 400, "airline": "Air France", "travel_class": cls, "flight_number": number}

    body = {"other_flights": [
        {"flights": [flight("AF 655", "Premium Economy"), flight("AF 1642", "Economy")], "total_duration": 670, "price": 1276},
        {"flights": [flight("AF 1", "Economy")], "total_duration": 400, "price": 300},
    ]}
    res = normalize(body, "DXB", "GVA", "2026-11-27", "premium", "USD")
    assert len(res.itineraries) == 1
    assert res.itineraries[0].other_cabin == ["AF 1642 Economy"]
