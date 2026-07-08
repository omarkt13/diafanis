from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import SourceRateLog

_DEFAULTS: dict[str, tuple[int, int]] = {
    "fred:": (120, 60),
    "yfinance:": (30, 60),
}
DEFAULT_LIMIT = 60
DEFAULT_WINDOW_S = 3600


def _limit_for(source_id: str) -> tuple[int, int]:
    for prefix, limits in _DEFAULTS.items():
        if source_id.startswith(prefix):
            return limits
    return DEFAULT_LIMIT, DEFAULT_WINDOW_S


def _window_start(now: datetime, window_s: int) -> datetime:
    bucket = int(now.timestamp() // window_s)
    return datetime.utcfromtimestamp(bucket * window_s)


def check_and_consume(db: Session, source_id: str, *, weight: int = 1) -> bool:
    """Returns True and records the call if `source_id` is under its limit
    for the current rolling window, False if the call should be skipped."""
    limit, window_s = _limit_for(source_id)
    window_start = _window_start(datetime.utcnow(), window_s)

    row = db.get(SourceRateLog, (source_id, window_start))
    if row is None:
        row = SourceRateLog(source_id=source_id, window_start=window_start, calls=0)
        db.add(row)
        db.flush()

    if row.calls + weight > limit:
        return False

    row.calls += weight
    db.commit()
    return True


def remaining_for(db: Session, source_id: str) -> int:
    limit, window_s = _limit_for(source_id)
    window_start = _window_start(datetime.utcnow(), window_s)
    row = db.get(SourceRateLog, (source_id, window_start))
    used = row.calls if row else 0
    return max(0, limit - used)
