from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class SourceRateLog(Base):
    """Rolling-window call counter keyed by (source_id, window_start), used to
    stay under external API rate limits (yfinance, FRED, ...)."""

    __tablename__ = "source_rate_log"

    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
