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
