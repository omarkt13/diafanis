from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class GPTrackRecord(Base):
    """A single prior-fund performance data point for a provider, sourced from
    public LP disclosures (e.g. CalPERS/CalSTRS quarterly PE performance
    reports). Feeds the alpha estimate for uncalibrated funds."""

    __tablename__ = "gp_track_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False, index=True)
    prior_fund_name: Mapped[str] = mapped_column(String, nullable=False)
    vintage_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tvpi: Mapped[float | None] = mapped_column(Float, nullable=True)
    dpi: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    provider = relationship("Provider", back_populates="track_records")
