from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Provider(Base):
    """A GP / fund sponsor. asset_class is the firm's primary class; each fund
    carries its own."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    asset_class: Mapped[str] = mapped_column(String, nullable=False, index=True)
    hq: Mapped[str | None] = mapped_column(String, nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aum_busd: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    funds = relationship("Fund", back_populates="provider", cascade="all, delete-orphan")
    track_records = relationship("GPTrackRecord", back_populates="provider", cascade="all, delete-orphan")
