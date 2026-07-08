from datetime import date

from pydantic import BaseModel, ConfigDict


class MetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    est_tvpi: float
    est_dpi: float
    est_rvpi: float
    est_nav_musd: float | None
    est_net_irr: float | None
    pme_alpha: float | None
    confidence: str
    narrative: str | None = None


class ProviderListItem(BaseModel):
    id: int
    name: str
    slug: str
    asset_class: str
    hq: str | None
    aum_busd: float | None
    description: str | None
    fund_count: int


class FundListItem(BaseModel):
    id: int
    name: str
    vintage_year: int
    fund_size_musd: float | None
    asset_class: str
    strategy: str | None
    status: str
    provider_name: str
    provider_slug: str
    est_tvpi: float | None = None
    est_net_irr: float | None = None
    pme_alpha: float | None = None
    confidence: str | None = None


class ProviderDetail(BaseModel):
    id: int
    name: str
    slug: str
    asset_class: str
    hq: str | None
    founded_year: int | None
    aum_busd: float | None
    description: str | None
    funds: list[FundListItem]


class ConstituentOut(BaseModel):
    ticker: str
    weight: float
    trailing_return_1y: float | None


class ExposureOut(BaseModel):
    sector_tag: str
    basket_name: str
    weight: float
    constituents: list[ConstituentOut]


class MacroOut(BaseModel):
    key: str
    label: str
    value: float


class FundDetail(BaseModel):
    id: int
    name: str
    vintage_year: int
    fund_size_musd: float | None
    asset_class: str
    strategy: str | None
    status: str
    provider_name: str
    provider_slug: str
    reported_tvpi: float | None
    reported_irr: float | None
    reported_as_of: date | None
    reported_source: str | None
    metrics: MetricsOut | None
    exposures: list[ExposureOut]
    macro: list[MacroOut]


class SeriesPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_date: date
    est_tvpi: float
    benchmark_tvpi: float
    est_nav_musd: float | None
