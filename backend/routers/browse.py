import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from deps import get_db
from models import Fund, FundMetrics, PriceCache, Provider, ValuationPoint
from schemas.api import (
    ConstituentOut,
    ExposureOut,
    FundDetail,
    FundListItem,
    MacroOut,
    MetricsOut,
    ProviderDetail,
    ProviderListItem,
    SeriesPoint,
)
from services import deepseek_client, market_data
from services.benchmarks import BASKETS, basket_name

router = APIRouter(tags=["browse"])


def _latest_metrics_map(db: Session, fund_ids: list[int]) -> dict[int, FundMetrics]:
    if not fund_ids:
        return {}
    sub = (
        db.query(FundMetrics.fund_id, func.max(FundMetrics.as_of_date).label("latest"))
        .filter(FundMetrics.fund_id.in_(fund_ids))
        .group_by(FundMetrics.fund_id)
        .subquery()
    )
    rows = (
        db.query(FundMetrics)
        .join(
            sub,
            and_(FundMetrics.fund_id == sub.c.fund_id, FundMetrics.as_of_date == sub.c.latest),
        )
        .all()
    )
    return {m.fund_id: m for m in rows}


def _fund_list_item(fund: Fund, metrics: FundMetrics | None) -> FundListItem:
    return FundListItem(
        id=fund.id,
        name=fund.name,
        vintage_year=fund.vintage_year,
        fund_size_musd=fund.fund_size_musd,
        asset_class=fund.asset_class,
        strategy=fund.strategy,
        status=fund.status,
        provider_name=fund.provider.name,
        provider_slug=fund.provider.slug,
        est_tvpi=metrics.est_tvpi if metrics else None,
        est_net_irr=metrics.est_net_irr if metrics else None,
        pme_alpha=metrics.pme_alpha if metrics else None,
        confidence=metrics.confidence if metrics else None,
    )


@router.get("/providers", response_model=list[ProviderListItem])
def list_providers(asset_class: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Provider, func.count(Fund.id)).outerjoin(Fund).group_by(Provider.id)
    if asset_class:
        query = query.filter(Provider.asset_class == asset_class)
    rows = query.order_by(Provider.aum_busd.desc().nullslast()).all()
    return [
        ProviderListItem(
            id=p.id,
            name=p.name,
            slug=p.slug,
            asset_class=p.asset_class,
            hq=p.hq,
            aum_busd=p.aum_busd,
            description=p.description,
            fund_count=count,
        )
        for p, count in rows
    ]


@router.get("/providers/{slug}", response_model=ProviderDetail)
def get_provider(slug: str, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.slug == slug).one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    funds = sorted(provider.funds, key=lambda f: f.vintage_year, reverse=True)
    metrics_map = _latest_metrics_map(db, [f.id for f in funds])
    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        asset_class=provider.asset_class,
        hq=provider.hq,
        founded_year=provider.founded_year,
        aum_busd=provider.aum_busd,
        description=provider.description,
        funds=[_fund_list_item(f, metrics_map.get(f.id)) for f in funds],
    )


@router.get("/funds", response_model=list[FundListItem])
def list_funds(
    asset_class: str | None = None,
    q: str | None = None,
    provider_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Fund).join(Provider)
    if asset_class:
        query = query.filter(Fund.asset_class == asset_class)
    if provider_id:
        query = query.filter(Fund.provider_id == provider_id)
    if q:
        pattern = f"%{q}%"
        query = query.filter(Fund.name.ilike(pattern) | Provider.name.ilike(pattern))
    funds = query.order_by(Fund.vintage_year.desc(), Fund.name).limit(300).all()
    metrics_map = _latest_metrics_map(db, [f.id for f in funds])
    return [_fund_list_item(f, metrics_map.get(f.id)) for f in funds]


MACRO_LABELS = {"ust10y": "US 10Y Treasury (%)", "cpi_yoy": "US CPI (index)", "medical_cpi_yoy": "Medical care CPI (index)"}


@router.get("/funds/{fund_id}", response_model=FundDetail)
def get_fund(fund_id: int, db: Session = Depends(get_db)):
    fund = db.get(Fund, fund_id)
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found")

    metrics_map = _latest_metrics_map(db, [fund.id])
    metrics = metrics_map.get(fund.id)
    if metrics is not None and metrics.narrative is None:
        metrics.narrative = deepseek_client.generate_fund_narrative(fund, metrics)
        db.commit()

    exposures: list[ExposureOut] = []
    exposure_weights: dict[str, float] = json.loads(fund.sector_exposures_json or "{}")
    trailing = {
        row.ticker: row.trailing_return_1y
        for row in db.query(PriceCache).all()
    }
    for tag, weight in sorted(exposure_weights.items(), key=lambda kv: -kv[1]):
        basket = BASKETS.get(tag, {"tickers": {}})
        total_w = sum(basket["tickers"].values()) or 1.0
        constituents = [
            ConstituentOut(
                ticker=ticker,
                weight=round(w / total_w, 3),
                trailing_return_1y=trailing.get(ticker),
            )
            for ticker, w in sorted(basket["tickers"].items(), key=lambda kv: -kv[1])
        ]
        exposures.append(
            ExposureOut(sector_tag=tag, basket_name=basket_name(tag), weight=weight, constituents=constituents)
        )

    macro = [
        MacroOut(key=key, label=label, value=market_data.get_macro_value(db, key))
        for key, label in MACRO_LABELS.items()
        if key in ("ust10y",)
    ]

    return FundDetail(
        id=fund.id,
        name=fund.name,
        vintage_year=fund.vintage_year,
        fund_size_musd=fund.fund_size_musd,
        asset_class=fund.asset_class,
        strategy=fund.strategy,
        status=fund.status,
        provider_name=fund.provider.name,
        provider_slug=fund.provider.slug,
        reported_tvpi=fund.reported_tvpi,
        reported_irr=fund.reported_irr,
        reported_as_of=fund.reported_as_of,
        reported_source=fund.reported_source,
        metrics=MetricsOut.model_validate(metrics) if metrics else None,
        exposures=exposures,
        macro=macro,
    )


@router.get("/funds/{fund_id}/series", response_model=list[SeriesPoint])
def get_fund_series(fund_id: int, db: Session = Depends(get_db)):
    fund = db.get(Fund, fund_id)
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found")
    return (
        db.query(ValuationPoint)
        .filter(ValuationPoint.fund_id == fund_id)
        .order_by(ValuationPoint.period_date)
        .all()
    )
