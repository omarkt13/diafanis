from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PriceCache(Base):
    __tablename__ = "price_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    trailing_return_1y: Mapped[float | None] = mapped_column(Float, nullable=True)
    history_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MacroSeriesCache(Base):
    __tablename__ = "macro_series_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
