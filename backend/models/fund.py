from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

ASSET_CLASSES = ("pe_buyout", "vc", "real_assets", "private_credit")
FUND_STATUSES = ("investing", "harvesting", "fully_realized")


class Fund(Base):
    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    vintage_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fund_size_musd: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset_class: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="harvesting")
    # JSON mapping of benchmark basket tag -> weight, weights sum to 1.0
    sector_exposures_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Last genuinely public mark (pension disclosure / GP report), used to
    # calibrate the model. All nullable — most funds have no public mark.
    reported_tvpi: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    reported_source: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    provider = relationship("Provider", back_populates="funds")
    metrics = relationship("FundMetrics", back_populates="fund", cascade="all, delete-orphan")
    series = relationship("ValuationPoint", back_populates="fund", cascade="all, delete-orphan")
