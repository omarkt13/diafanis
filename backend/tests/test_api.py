import pytest

from models import Fund, Provider
from seed_data.seed import seed_if_empty
from services.refresh import refresh_fund


@pytest.fixture()
def seeded_client(client, db_session):
    seed_if_empty(db_session)
    blackstone = db_session.query(Provider).filter(Provider.slug == "blackstone").one()
    for fund in blackstone.funds:
        refresh_fund(db_session, fund)
    return client


def test_list_providers(seeded_client):
    resp = seeded_client.get("/api/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) >= 45
    assert all(p["fund_count"] > 0 for p in providers)

    resp = seeded_client.get("/api/providers?asset_class=vc")
    assert all(p["asset_class"] == "vc" for p in resp.json())


def test_provider_detail_includes_fund_metrics(seeded_client):
    resp = seeded_client.get("/api/providers/blackstone")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Blackstone"
    assert len(body["funds"]) >= 4
    with_metrics = [f for f in body["funds"] if f["est_tvpi"] is not None]
    assert with_metrics, "refreshed funds should expose metrics"


def test_fund_search_and_filters(seeded_client):
    resp = seeded_client.get("/api/funds?q=Sequoia")
    assert resp.status_code == 200
    assert all("sequoia" in f["provider_name"].lower() for f in resp.json())

    resp = seeded_client.get("/api/funds?asset_class=private_credit")
    assert all(f["asset_class"] == "private_credit" for f in resp.json())


def test_fund_detail_and_series(seeded_client, db_session):
    fund = (
        db_session.query(Fund)
        .join(Provider)
        .filter(Provider.slug == "blackstone", Fund.reported_tvpi.isnot(None))
        .first()
    )
    resp = seeded_client.get(f"/api/funds/{fund.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metrics"] is not None
    assert body["metrics"]["confidence"] == "high"
    assert body["metrics"]["narrative"]  # lazily generated deterministic text
    assert body["exposures"], "benchmark breakdown missing"
    assert body["exposures"][0]["constituents"]

    series = seeded_client.get(f"/api/funds/{fund.id}/series").json()
    assert len(series) >= 8
    dates = [p["period_date"] for p in series]
    assert dates == sorted(dates)
    last = series[-1]
    assert abs(last["est_tvpi"] - body["metrics"]["est_tvpi"]) < 0.01


def test_fund_not_found(seeded_client):
    assert seeded_client.get("/api/funds/99999").status_code == 404
    assert seeded_client.get("/api/providers/nonexistent").status_code == 404
