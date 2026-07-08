from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class FundMetrics(Base):
    """Latest model-estimated headline metrics for a fund, one row per fund
    per refresh date."""

    __tablename__ = "fund_metrics"
    __table_args__ = (UniqueConstraint("fund_id", "as_of_date", name="uq_fund_metrics_fund_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    est_tvpi: Mapped[float] = mapped_column(Float, nullable=False)
    est_dpi: Mapped[float] = mapped_column(Float, nullable=False)
    est_rvpi: Mapped[float] = mapped_column(Float, nullable=False)
    est_nav_musd: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_net_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    pme_alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False, default="low")
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    fund = relationship("Fund", back_populates="metrics")


class ValuationPoint(Base):
    """Quarterly estimate-of-value series point, for the fund detail graph."""

    __tablename__ = "valuation_points"
    __table_args__ = (UniqueConstraint("fund_id", "period_date", name="uq_valuation_point_fund_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    est_tvpi: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_tvpi: Mapped[float] = mapped_column(Float, nullable=False)
    est_nav_musd: Mapped[float | None] = mapped_column(Float, nullable=True)

    fund = relationship("Fund", back_populates="series")
