"""Idempotent seeder: loads the curated provider/fund universe when the DB is
empty. Funds with public reported marks also produce GPTrackRecord rows for
their provider, which feed the alpha estimate for uncalibrated sibling funds."""

import json
import logging

from sqlalchemy.orm import Session

from models import Fund, GPTrackRecord, Provider
from seed_data.funds import FUNDS
from seed_data.providers import PROVIDERS

logger = logging.getLogger("diafanis.seed")


def default_status(vintage_year: int) -> str:
    if vintage_year >= 2022:
        return "investing"
    if vintage_year >= 2013:
        return "harvesting"
    return "fully_realized"


def seed_if_empty(db: Session) -> bool:
    if db.query(Provider).count() > 0:
        return False

    providers_by_slug: dict[str, Provider] = {}
    for p in PROVIDERS:
        provider = Provider(**p)
        db.add(provider)
        providers_by_slug[p["slug"]] = provider
    db.flush()

    for f in FUNDS:
        provider = providers_by_slug[f["provider"]]
        reported = f.get("reported") or {}
        fund = Fund(
            provider_id=provider.id,
            name=f["name"],
            vintage_year=f["vintage_year"],
            fund_size_musd=f["fund_size_musd"],
            asset_class=f["asset_class"],
            strategy=f["strategy"],
            status=f.get("status") or default_status(f["vintage_year"]),
            sector_exposures_json=json.dumps(f["exposures"]),
            reported_tvpi=reported.get("tvpi"),
            reported_irr=reported.get("irr"),
            reported_as_of=reported.get("as_of"),
            reported_source=reported.get("source"),
        )
        db.add(fund)

        if reported.get("tvpi"):
            db.add(
                GPTrackRecord(
                    provider_id=provider.id,
                    prior_fund_name=f["name"],
                    vintage_year=f["vintage_year"],
                    irr=reported.get("irr"),
                    tvpi=reported.get("tvpi"),
                    source=reported.get("source") or "seed",
                    as_of_date=reported["as_of"],
                )
            )

    db.commit()
    logger.info("Seeded %d providers and %d funds", len(PROVIDERS), len(FUNDS))
    return True
