"""Daily valuation refresh: pull fresh comp histories, recompute every fund's
quarterly series and headline metrics, and persist them so the browse API
reads only from the DB."""

import logging
import os
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Fund, FundMetrics, ValuationPoint
from services.valuation_engine import compute_fund_valuation

logger = logging.getLogger("diafanis.refresh")


def refresh_fund(db: Session, fund: Fund, as_of: date | None = None) -> FundMetrics:
    as_of = as_of or date.today()
    result = compute_fund_valuation(db, fund, as_of)
    latest = result.latest

    db.query(ValuationPoint).filter(ValuationPoint.fund_id == fund.id).delete()
    for q in result.quarters:
        db.add(
            ValuationPoint(
                fund_id=fund.id,
                period_date=q.period_date,
                est_tvpi=q.est_tvpi,
                benchmark_tvpi=q.benchmark_tvpi,
                est_nav_musd=(
                    round(q.nav_gross * q.net_factor * fund.fund_size_musd, 1)
                    if fund.fund_size_musd
                    else None
                ),
            )
        )

    metrics = (
        db.query(FundMetrics)
        .filter(FundMetrics.fund_id == fund.id, FundMetrics.as_of_date == as_of)
        .one_or_none()
    )
    if metrics is None:
        metrics = FundMetrics(fund_id=fund.id, as_of_date=as_of, est_tvpi=0, est_dpi=0, est_rvpi=0)
        db.add(metrics)
    metrics.est_tvpi = latest.est_tvpi
    metrics.est_dpi = latest.est_dpi
    metrics.est_rvpi = latest.est_rvpi
    metrics.est_nav_musd = (
        round(latest.nav_gross * latest.net_factor * fund.fund_size_musd, 1)
        if fund.fund_size_musd
        else None
    )
    metrics.est_net_irr = result.est_net_irr
    metrics.pme_alpha = result.pme_alpha
    metrics.confidence = result.confidence
    metrics.narrative = None  # regenerated lazily on first fund-detail view
    db.commit()
    return metrics


def refresh_all(db: Session, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    funds = db.query(Fund).all()
    count = 0
    for fund in funds:
        try:
            refresh_fund(db, fund, as_of)
            count += 1
        except Exception:
            logger.exception("Refresh failed for fund %s (%s)", fund.id, fund.name)
            db.rollback()
    logger.info("Refreshed %d/%d funds for %s", count, len(funds), as_of)
    return count


def is_stale(db: Session) -> bool:
    latest = db.query(func.max(FundMetrics.as_of_date)).scalar()
    return latest is None or latest < date.today()


def run_refresh_job() -> None:
    """Entry point for the scheduler (runs in a worker thread with its own
    session)."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    db = SessionLocal()
    try:
        refresh_all(db)
    finally:
        db.close()


def run_startup_catchup() -> None:
    db = SessionLocal()
    try:
        if is_stale(db):
            logger.info("Metrics stale — running startup refresh")
            refresh_all(db)
    finally:
        db.close()
