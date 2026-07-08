from datetime import datetime, timedelta

from services import rate_limit as rl


class FrozenDateTime(datetime):
    _now = datetime(2026, 1, 1, 0, 0, 0)

    @classmethod
    def utcnow(cls):
        return cls._now


def test_rate_limit_blocks_after_limit(db_session, monkeypatch):
    monkeypatch.setattr(rl, "datetime", FrozenDateTime)
    source_id = "yfinance:TEST"
    limit, _window_s = rl._limit_for(source_id)

    for _ in range(limit):
        assert rl.check_and_consume(db_session, source_id) is True

    assert rl.check_and_consume(db_session, source_id) is False


def test_rate_limit_resets_in_new_window(db_session, monkeypatch):
    monkeypatch.setattr(rl, "datetime", FrozenDateTime)
    FrozenDateTime._now = datetime(2026, 1, 1, 0, 0, 0)
    source_id = "yfinance:TEST2"
    limit, window_s = rl._limit_for(source_id)

    for _ in range(limit):
        rl.check_and_consume(db_session, source_id)
    assert rl.check_and_consume(db_session, source_id) is False

    FrozenDateTime._now = FrozenDateTime._now + timedelta(seconds=window_s + 1)
    assert rl.check_and_consume(db_session, source_id) is True
