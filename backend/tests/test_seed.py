import json

from models import Fund, GPTrackRecord, Provider
from seed_data.seed import seed_if_empty
from services.benchmarks import BASKETS


def test_seed_populates_universe(db_session):
    assert seed_if_empty(db_session) is True
    assert db_session.query(Provider).count() >= 45
    assert db_session.query(Fund).count() >= 140
    assert db_session.query(GPTrackRecord).count() >= 50


def test_seed_is_idempotent(db_session):
    assert seed_if_empty(db_session) is True
    fund_count = db_session.query(Fund).count()
    assert seed_if_empty(db_session) is False
    assert db_session.query(Fund).count() == fund_count


def test_fund_exposures_are_valid(db_session):
    seed_if_empty(db_session)
    for fund in db_session.query(Fund).all():
        exposures = json.loads(fund.sector_exposures_json)
        assert exposures, f"{fund.name} has no exposures"
        assert abs(sum(exposures.values()) - 1.0) < 0.01, f"{fund.name} weights don't sum to 1"
        for tag in exposures:
            assert tag in BASKETS, f"{fund.name} references unknown basket {tag}"


def test_reported_marks_have_sources(db_session):
    seed_if_empty(db_session)
    for fund in db_session.query(Fund).filter(Fund.reported_tvpi.isnot(None)).all():
        assert fund.reported_as_of is not None
        assert fund.reported_source
