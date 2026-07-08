"""Public-market data layer: monthly close histories per ticker (yfinance),
macro series (FRED), both cached in the DB with a ~daily TTL and backed by
deterministic seeded fallbacks so the app and tests work with no network and
no API keys."""

import hashlib
import json
import logging
import math
import os
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from config import get_settings
from models import MacroSeriesCache, PriceCache
from services import rate_limit
from services.benchmarks import BASKETS

logger = logging.getLogger("diafanis.market_data")

CACHE_TTL_HOURS = 20  # refreshed by the daily job; anything younger is reused

FALLBACK_HISTORY_START = (2000, 1)

FRED_SERIES = {
    "ust10y": "DGS10",
    "medical_cpi_yoy": "CUSR0000SAM2",
    "cpi_yoy": "CPIAUCSL",
}

_FALLBACK_MACRO = {
    "ust10y": 4.25,
    "medical_cpi_yoy": 3.8,
    "cpi_yoy": 2.9,
}


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _is_cache_stale(fetched_at: datetime, ttl_hours: int = CACHE_TTL_HOURS) -> bool:
    return datetime.utcnow() - fetched_at > timedelta(hours=ttl_hours)


def month_keys(start: tuple[int, int], end: tuple[int, int]) -> list[str]:
    """Inclusive list of 'YYYY-MM' keys from start to end."""
    keys = []
    year, month = start
    while (year, month) <= end:
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return keys


def _seeded_unit(*parts: str) -> float:
    """Deterministic pseudo-random float in [-1, 1) from string parts."""
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return (int(digest[:12], 16) / 16**12) * 2 - 1


def _deterministic_monthly_closes(ticker: str) -> dict[str, float]:
    """Seeded geometric walk, used when yfinance is unavailable or in tests.
    Per-ticker drift in ~[2%, 14%]/yr, monthly vol ~4%."""
    drift_annual = 0.02 + (abs(_seeded_unit(ticker, "drift"))) * 0.12
    drift_monthly = (1 + drift_annual) ** (1 / 12) - 1
    now = datetime.utcnow()
    closes: dict[str, float] = {}
    price = 25.0 + abs(_seeded_unit(ticker, "p0")) * 175.0
    for key in month_keys(FALLBACK_HISTORY_START, (now.year, now.month)):
        shock = _seeded_unit(ticker, key) * 0.04
        price = max(1.0, price * (1 + drift_monthly + shock))
        closes[key] = round(price, 4)
    return closes


def _fetch_monthly_closes_yfinance(db: Session, ticker: str) -> dict[str, float] | None:
    if _is_test_runtime():
        return None
    if not rate_limit.check_and_consume(db, f"yfinance:{ticker}"):
        logger.warning("yfinance rate limit hit for %s", ticker)
        return None
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="max", interval="1mo", timeout=10)
        if hist is None or len(hist) < 12:
            return None
        closes: dict[str, float] = {}
        for ts, row in hist.iterrows():
            close = float(row["Close"])
            if close > 0 and not math.isnan(close):
                closes[f"{ts.year:04d}-{ts.month:02d}"] = round(close, 4)
        return closes or None
    except Exception:
        logger.warning("yfinance fetch failed for %s", ticker, exc_info=True)
        return None


def get_monthly_closes(db: Session, ticker: str) -> dict[str, float]:
    """Month-key -> close price for `ticker`, cached with a ~daily TTL,
    falling back to a deterministic seeded walk."""
    cached = db.query(PriceCache).filter(PriceCache.ticker == ticker).one_or_none()
    if cached and cached.history_json and not _is_cache_stale(cached.fetched_at):
        return json.loads(cached.history_json)

    closes = _fetch_monthly_closes_yfinance(db, ticker)
    if closes is None:
        closes = _deterministic_monthly_closes(ticker)

    keys = sorted(closes)
    trailing_1y = None
    if len(keys) >= 13:
        start, end = closes[keys[-13]], closes[keys[-1]]
        if start > 0:
            trailing_1y = round(end / start - 1, 4)

    if cached:
        cached.history_json = json.dumps(closes)
        cached.trailing_return_1y = trailing_1y
        cached.as_of_date = date.today()
        cached.fetched_at = datetime.utcnow()
    else:
        db.add(
            PriceCache(
                ticker=ticker,
                as_of_date=date.today(),
                trailing_return_1y=trailing_1y,
                history_json=json.dumps(closes),
            )
        )
    db.commit()
    return closes


def get_trailing_return_1y(db: Session, ticker: str) -> float | None:
    closes = get_monthly_closes(db, ticker)
    keys = sorted(closes)
    if len(keys) < 13:
        return None
    start, end = closes[keys[-13]], closes[keys[-1]]
    return round(end / start - 1, 4) if start > 0 else None


def build_basket_monthly_returns(db: Session, sector_tag: str, start: tuple[int, int]) -> dict[str, float]:
    """Weighted monthly return series for a benchmark basket from `start` to
    the current month. Months predating a ticker's history simply exclude that
    ticker; months with no constituent data use a seeded fallback return."""
    basket = BASKETS.get(sector_tag)
    now = datetime.utcnow()
    keys = month_keys(start, (now.year, now.month))

    if not basket:
        return {key: _seeded_unit(sector_tag, key) * 0.03 + 0.005 for key in keys}

    ticker_closes = {ticker: get_monthly_closes(db, ticker) for ticker in basket["tickers"]}

    returns: dict[str, float] = {}
    prev_key: str | None = None
    for key in keys:
        if prev_key is not None:
            weighted, total_weight = 0.0, 0.0
            for ticker, weight in basket["tickers"].items():
                closes = ticker_closes[ticker]
                if key in closes and prev_key in closes and closes[prev_key] > 0:
                    weighted += (closes[key] / closes[prev_key] - 1) * weight
                    total_weight += weight
            if total_weight > 0:
                returns[key] = weighted / total_weight
            else:
                returns[key] = _seeded_unit(sector_tag, key) * 0.03 + 0.005
        prev_key = key
    return returns


def _fetch_macro_fred(db: Session, series_key: str, fred_series_id: str) -> float | None:
    settings = get_settings()
    if _is_test_runtime() or not settings.fred_api_key:
        return None
    if not rate_limit.check_and_consume(db, f"fred:{series_key}"):
        logger.warning("FRED rate limit hit for %s", series_key)
        return None
    try:
        from fredapi import Fred

        fred = Fred(api_key=settings.fred_api_key)
        series = fred.get_series(fred_series_id, observation_start="2020-01-01").dropna()
        if series.empty:
            return None
        return round(float(series.iloc[-1]), 4)
    except Exception:
        logger.warning("FRED fetch failed for %s", series_key, exc_info=True)
        return None


def get_macro_value(db: Session, series_key: str) -> float:
    """Latest value for a named macro series, cached with a ~daily TTL,
    falling back to a hardcoded plausible default."""
    cached = db.query(MacroSeriesCache).filter(MacroSeriesCache.series_key == series_key).one_or_none()
    if cached and not _is_cache_stale(cached.fetched_at):
        return cached.value

    fred_series_id = FRED_SERIES.get(series_key)
    value = _fetch_macro_fred(db, series_key, fred_series_id) if fred_series_id else None
    if value is None:
        value = _FALLBACK_MACRO.get(series_key, 0.0)

    if cached:
        cached.value = value
        cached.as_of_date = date.today()
        cached.fetched_at = datetime.utcnow()
    else:
        db.add(MacroSeriesCache(series_key=series_key, value=value, as_of_date=date.today()))
    db.commit()
    return value
