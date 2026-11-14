"""Stand-in for SerpApi, for UI work without spending searches.

It returns made-up fares in the documented google_flights format. Run it, then
start the app with SERPAPI_URL=http://127.0.0.1:8099/search.json SERPAPI_KEY=fake.
The prices are NOT real.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI()
SCALE = {"1": 0.19, "2": 0.43, "3": 1.0, "4": 2.6}


def seg(fn, airline, o, d, day, dep, arr, dur, plus=0):
    from datetime import date, timedelta

    day2 = (date.fromisoformat(day) + timedelta(days=plus)).isoformat()
    return {"departure_airport": {"id": o, "time": f"{day} {dep}"}, "arrival_airport": {"id": d, "time": f"{day2} {arr}"},
            "duration": dur, "airplane": "Airbus A350", "airline": airline, "travel_class": "", "flight_number": fn}


LABEL = {"1": "Economy", "2": "Premium Economy", "3": "Business Class", "4": "First Class"}


def item(price, segs, total):
    return {"flights": segs, "total_duration": total, "price": round(price), "type": "One way"}


@app.get("/search.json")
def search(departure_id: str, arrival_id: str, outbound_date: str, type: str = "2", travel_class: str = "1", return_date: str | None = None):
    k, day, o = SCALE.get(travel_class, 1.0), outbound_date, departure_id
    return _label(_search(k, day, o, arrival_id, type), LABEL.get(travel_class, "Economy"))


def _label(body, label):
    for key in ("best_flights", "other_flights"):
        for it in body.get(key) or []:
            it["flights"] = [{**f, "travel_class": label} for f in it["flights"]]
    return body


def _search(k, day, o, arrival_id, type):
    dests = arrival_id.split(",")
    d = dests[0]
    hub = "IST" if "IST" not in (o, d) else "DOH"
    via = [seg("TK 759", "Turkish Airlines", o, hub, day, "09:30", "13:20", 290), seg("TK 1919", "Turkish Airlines", hub, d, day, "15:30", "17:10", 220)]
    non = [seg("EK 89", "Emirates", o, d, day, "14:40", "18:45", 425)]
    if len(dests) > 1:  # hidden-city search: a through ticket that stops at the first listed... the real destination is not in the list
        real = "GVA" if o != "GVA" else "DXB"
        beyond = dests[0]
        return {"best_flights": [], "other_flights": [
            item(3050 * k, [seg("EK 89", "Emirates", o, real, day, "14:40", "18:45", 425), seg("LX 352", "SWISS", real, beyond, day, "20:10", "20:55", 105)], 615),
            item(2500 * k, [seg("BA 106", "British Airways", o, beyond, day, "08:00", "12:10", 430)], 430),
        ]}
    if type == "1":
        return {"best_flights": [item(2310 * k, via, 640)], "other_flights": [item(6900 * k, non, 425)]}
    return {
        "best_flights": [item(2896 * k, via, 640), item(4100 * k, non, 425)],
        "other_flights": [item(3380 * k, [seg("LX 243", "SWISS", o, "ZRH", day, "01:10", "05:40", 450), seg("LX 2802", "SWISS", "ZRH", d, day, "07:05", "07:55", 50)], 585)],
        "price_insights": {"lowest_price": round(2896 * k), "price_level": "low", "typical_price_range": [round(3000 * k), round(4400 * k)]},
    }
