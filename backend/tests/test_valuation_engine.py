import json
from datetime import date

from models import Fund, Provider
from services.valuation_engine import (
    QuarterState,
    _net_irr,
    compute_fund_valuation,
    quarter_ends,
)


def _make_fund(db, **overrides):
    provider = db.query(Provider).filter(Provider.slug == "test-gp").one_or_none()
    if provider is None:
        provider = Provider(name="Test GP", slug="test-gp", asset_class="pe_buyout")
        db.add(provider)
        db.flush()
    defaults = dict(
        provider_id=provider.id,
        name="Test Fund I",
        vintage_year=2018,
        fund_size_musd=1000.0,
        asset_class="pe_buyout",
        status="harvesting",
        sector_exposures_json=json.dumps({"diversified_buyout": 1.0}),
    )
    defaults.update(overrides)
    fund = Fund(**defaults)
    db.add(fund)
    db.commit()
    return fund


def test_quarter_ends_span_vintage_to_today():
    ends = quarter_ends(2020, date(2022, 8, 15))
    assert ends[0] == date(2020, 3, 31)
    assert ends[-1] == date(2022, 6, 30)
    assert len(ends) == 10


def test_tvpi_identity_and_contribution_cap(db_session):
    fund = _make_fund(db_session)
    result = compute_fund_valuation(db_session, fund, as_of=date(2025, 12, 31))
    latest = result.latest

    assert abs(latest.est_tvpi - (latest.est_dpi + latest.est_rvpi)) < 0.01
    assert latest.cum_contrib <= 1.001  # never draws more than the commitment
    assert latest.est_tvpi > 0
    assert result.confidence == "low"  # no mark, no track record


def test_calibration_passes_through_reported_mark(db_session):
    fund = _make_fund(
        db_session,
        name="Calibrated Fund",
        reported_tvpi=1.8,
        reported_as_of=date(2024, 12, 31),
        reported_source="test disclosure",
    )
    result = compute_fund_valuation(db_session, fund, as_of=date(2025, 12, 31))
    assert result.confidence == "high"

    report_q = [q for q in result.quarters if q.period_date == date(2024, 12, 31)]
    assert report_q, "report quarter missing from series"
    assert abs(report_q[0].est_tvpi - 1.8) < 0.02


def test_fully_realized_fund_ends_with_no_nav(db_session):
    fund = _make_fund(db_session, name="Old Fund", vintage_year=2008, status="fully_realized")
    result = compute_fund_valuation(db_session, fund, as_of=date(2025, 12, 31))
    assert result.latest.est_rvpi == 0
    assert result.latest.est_dpi == result.latest.est_tvpi


def test_net_irr_on_known_cashflows():
    # -1.0 at Q1, +2.0 at Q20: (1+r_q)^19 = 2 -> ~15.7% annualized
    states = []
    for i in range(20):
        s = QuarterState(period_date=date(2020, 3, 31))
        s.net_factor = 1.0
        states.append(s)
    states[0].contribution = 1.0
    states[19].dist_gross = 2.0
    for s in states:
        s.cum_contrib = 1.0
    irr = _net_irr(states)
    assert irr is not None
    assert abs(irr - 0.157) < 0.01


def test_credit_fund_distributes_early(db_session):
    fund = _make_fund(
        db_session,
        name="Credit Fund",
        vintage_year=2021,
        asset_class="private_credit",
        sector_exposures_json=json.dumps({"leveraged_credit": 1.0}),
    )
    result = compute_fund_valuation(db_session, fund, as_of=date(2024, 12, 31))
    assert result.latest.est_dpi > 0.1  # income distributions from year one


def test_pme_alpha_present(db_session):
    fund = _make_fund(db_session, name="PME Fund")
    result = compute_fund_valuation(db_session, fund, as_of=date(2025, 12, 31))
    assert result.pme_alpha is not None
    assert -1.0 < result.pme_alpha < 2.0
