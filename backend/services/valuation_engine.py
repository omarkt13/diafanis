"""Model-estimated private fund valuation.

Simplified Takahashi-Alexander pacing model with comp-indexed growth:
contributions are drawn over the investment period, deployed capital compounds
at the fund's sector-weighted public benchmark return scaled by an asset-class
beta plus a GP alpha spread, exits pace up from mid-life, and management fees
plus carried interest (20% over an 8% pref) reduce everything to net-of-fee.

Where a fund has a genuinely public reported mark (pension disclosure / GP
report), the alpha spread is solved so the model passes through that mark and
is then rolled forward with benchmark returns — "public benchmark roll-forward
from the last disclosed mark". Confidence tags surface which mode produced
each estimate.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from models import Fund, GPTrackRecord
from services import market_data

logger = logging.getLogger("diafanis.valuation")

QUARTERLY_PREF = 1.08 ** 0.25  # 8% annual preferred return, compounded quarterly
CARRY_RATE = 0.20

CLASS_PARAMS: dict[str, dict] = {
    "pe_buyout": {
        "beta": 1.4,
        "invest_years": 5.0,
        "call_rate_q": 0.09,
        "exit_start_yr": 4.0,
        "exit_base_q": 0.03,
        "exit_ramp_q": 0.008,
        "income_yield_q": 0.0,
        "fee_committed_q": 0.005,   # 2.0%/yr on committed during investment period
        "fee_nav_q": 0.00375,       # 1.5%/yr on NAV after
        "default_sector": "diversified_buyout",
    },
    "vc": {
        "beta": 1.6,
        "invest_years": 4.0,
        "call_rate_q": 0.11,
        "exit_start_yr": 5.5,
        "exit_base_q": 0.025,
        "exit_ramp_q": 0.006,
        "income_yield_q": 0.0,
        "fee_committed_q": 0.00625,  # 2.5%/yr, typical of venture
        "fee_nav_q": 0.005,
        "default_sector": "growth_equity",
    },
    "real_assets": {
        "beta": 0.9,
        "invest_years": 4.0,
        "call_rate_q": 0.10,
        "exit_start_yr": 4.0,
        "exit_base_q": 0.025,
        "exit_ramp_q": 0.006,
        "income_yield_q": 0.008,     # ~3.2%/yr income distributions
        "fee_committed_q": 0.00375,
        "fee_nav_q": 0.003,
        "default_sector": "energy_infrastructure",
    },
    "private_credit": {
        "beta": 0.5,
        "invest_years": 3.0,
        "call_rate_q": 0.14,
        "exit_start_yr": 2.5,        # principal amortization starts early
        "exit_base_q": 0.05,
        "exit_ramp_q": 0.008,
        "income_yield_q": 0.022,     # ~9%/yr income distributions
        "fee_committed_q": 0.00325,
        "fee_nav_q": 0.0025,
        "default_sector": "leveraged_credit",
    },
}

MAX_EXIT_FRAC_Q = 0.15


@dataclass
class QuarterState:
    period_date: date
    contribution: float = 0.0
    dist_gross: float = 0.0
    cum_contrib: float = 0.0
    cum_dist_gross: float = 0.0
    nav_gross: float = 0.0
    net_factor: float = 1.0
    est_tvpi: float = 0.0
    est_dpi: float = 0.0
    est_rvpi: float = 0.0
    benchmark_tvpi: float = 1.0
    benchmark_level: float = 1.0


@dataclass
class ValuationResult:
    quarters: list[QuarterState] = field(default_factory=list)
    alpha_annual: float = 0.0
    confidence: str = "low"
    est_net_irr: float | None = None
    pme_alpha: float | None = None

    @property
    def latest(self) -> QuarterState:
        return self.quarters[-1]


def quarter_ends(vintage_year: int, until: date) -> list[date]:
    """Calendar quarter-end dates from the fund's vintage year through today."""
    ends = []
    for year in range(vintage_year, until.year + 1):
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            q_end = date(year, month, day)
            if q_end <= until:
                ends.append(q_end)
    return ends


def _blended_quarterly_returns(db: Session, fund: Fund, quarters: list[date]) -> list[float]:
    """Sector-weighted benchmark return per quarter, compounded from the
    blended monthly basket returns."""
    exposures: dict[str, float] = json.loads(fund.sector_exposures_json or "{}")
    if not exposures:
        exposures = {CLASS_PARAMS[fund.asset_class]["default_sector"]: 1.0}
    total_w = sum(exposures.values()) or 1.0

    start = (fund.vintage_year - 1, 12)
    tag_returns = {
        tag: market_data.build_basket_monthly_returns(db, tag, start) for tag in exposures
    }

    q_returns = []
    for q_end in quarters:
        compounded = 1.0
        for offset in (2, 1, 0):
            month = q_end.month - offset
            year = q_end.year
            if month <= 0:
                month += 12
                year -= 1
            key = f"{year:04d}-{month:02d}"
            blended = sum(
                tag_returns[tag].get(key, 0.0) * weight for tag, weight in exposures.items()
            ) / total_w
            compounded *= 1 + blended
        q_returns.append(compounded - 1)
    return q_returns


def _simulate(
    fund: Fund,
    quarters: list[date],
    q_returns: list[float],
    alpha_annual: float,
) -> list[QuarterState]:
    params = CLASS_PARAMS[fund.asset_class]
    alpha_q = alpha_annual / 4
    beta = params["beta"]

    undrawn = 1.0
    nav = 0.0
    cum_contrib = 0.0
    cum_dist = 0.0
    pref_base = 0.0
    bench_wealth = 0.0
    bench_level = 1.0

    states: list[QuarterState] = []
    n = len(quarters)
    for i, (q_end, r_q) in enumerate(zip(quarters, q_returns)):
        age_years = (i + 1) / 4

        # --- capital calls (investments + fees, both drawn from commitment) ---
        if age_years <= params["invest_years"]:
            call_inv = undrawn * params["call_rate_q"]
            fee = params["fee_committed_q"]
        else:
            call_inv = undrawn * 0.02  # small tail draws for follow-ons
            fee = params["fee_nav_q"] * nav
        undrawn -= call_inv
        fee_draw = min(undrawn, fee)
        undrawn -= fee_draw
        fee_from_nav = fee - fee_draw
        contribution = call_inv + fee_draw

        # --- growth ---
        nav = nav * (1 + beta * r_q + alpha_q) + call_inv - fee_from_nav
        nav = max(0.0, nav)

        # --- distributions ---
        dist = 0.0
        if params["income_yield_q"] > 0 and nav > 0:
            income = nav * params["income_yield_q"]
            nav -= income
            dist += income
        if age_years >= params["exit_start_yr"] and nav > 0:
            frac = min(
                params["exit_base_q"] + params["exit_ramp_q"] * (age_years - params["exit_start_yr"]) * 4,
                MAX_EXIT_FRAC_Q,
            )
            exit_amt = nav * frac
            nav -= exit_amt
            dist += exit_amt
        if fund.status == "fully_realized" and i == n - 1 and nav > 0:
            dist += nav
            nav = 0.0

        cum_contrib += contribution
        cum_dist += dist
        pref_base = pref_base * QUARTERLY_PREF + contribution

        # --- carry (20% of value above the 8% pref), applied pro-rata ---
        tv_gross = cum_dist + nav
        carry = CARRY_RATE * max(0.0, tv_gross - pref_base)
        net_factor = 1 - carry / tv_gross if tv_gross > 0 else 1.0

        # --- benchmark: same contributions invested in the blended index ---
        bench_level *= 1 + r_q
        bench_wealth = bench_wealth * (1 + r_q) + contribution

        state = QuarterState(period_date=q_end, contribution=contribution, dist_gross=dist)
        state.cum_contrib = cum_contrib
        state.cum_dist_gross = cum_dist
        state.nav_gross = nav
        state.net_factor = net_factor
        if cum_contrib > 0:
            state.est_tvpi = round(tv_gross * net_factor / cum_contrib, 4)
            state.est_dpi = round(cum_dist * net_factor / cum_contrib, 4)
            state.est_rvpi = round(nav * net_factor / cum_contrib, 4)
            state.benchmark_tvpi = round(bench_wealth / cum_contrib, 4)
        state.benchmark_level = bench_level
        states.append(state)
    return states


def _net_irr(states: list[QuarterState]) -> float | None:
    """Annualized net IRR via bisection on the quarterly cashflows plus the
    terminal net NAV."""
    if len(states) < 6 or states[-1].cum_contrib <= 0.01:
        return None
    flows = [-s.contribution + s.dist_gross * s.net_factor for s in states]
    flows[-1] += states[-1].nav_gross * states[-1].net_factor
    if all(f <= 0 for f in flows):
        return None

    def npv(rate_q: float) -> float:
        return sum(f / (1 + rate_q) ** (i + 1) for i, f in enumerate(flows))

    lo, hi = -0.5, 1.0
    if npv(lo) < 0 or npv(hi) > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    rate_q = (lo + hi) / 2
    return round((1 + rate_q) ** 4 - 1, 4)


def _pme_alpha(states: list[QuarterState]) -> float | None:
    """Kaplan-Schoar PME minus 1: >0 means the fund beat its blended public
    benchmark on a cash-weighted basis."""
    final_level = states[-1].benchmark_level
    if final_level <= 0:
        return None
    contrib_fv = 0.0
    dist_fv = 0.0
    for s in states:
        scale = final_level / s.benchmark_level
        contrib_fv += s.contribution * scale
        dist_fv += s.dist_gross * s.net_factor * scale
    dist_fv += states[-1].nav_gross * states[-1].net_factor
    if contrib_fv <= 0:
        return None
    return round(dist_fv / contrib_fv - 1, 4)


def _track_record_alpha(db: Session, provider_id: int) -> float | None:
    """Annual alpha spread implied by the provider's public track record:
    average net IRR (or TVPI-implied IRR over ~8 years) versus a 14% PE-market
    baseline, clamped to a modest band."""
    records = db.query(GPTrackRecord).filter(GPTrackRecord.provider_id == provider_id).all()
    implied: list[float] = []
    for r in records:
        if r.irr is not None:
            implied.append(r.irr)
        elif r.tvpi is not None and r.tvpi > 0:
            implied.append(r.tvpi ** (1 / 8) - 1)
    if not implied:
        return None
    avg = sum(implied) / len(implied)
    return max(-0.08, min(0.10, avg - 0.14))


def _calibrate_alpha(
    fund: Fund,
    quarters: list[date],
    q_returns: list[float],
) -> float | None:
    """Solve the annual alpha so the modeled TVPI passes through the fund's
    reported mark at its report date. TVPI is monotonic in alpha."""
    if fund.reported_tvpi is None or fund.reported_as_of is None:
        return None
    target_idx = min(
        range(len(quarters)),
        key=lambda i: abs((quarters[i] - fund.reported_as_of).days),
    )
    if target_idx < 3:
        return None

    def tvpi_at(alpha: float) -> float:
        return _simulate(fund, quarters, q_returns, alpha)[target_idx].est_tvpi

    lo, hi = -0.30, 0.45
    if tvpi_at(lo) > fund.reported_tvpi or tvpi_at(hi) < fund.reported_tvpi:
        return max(lo, min(hi, 0.0))  # unreachable mark: fall back to neutral
    for _ in range(40):
        mid = (lo + hi) / 2
        if tvpi_at(mid) < fund.reported_tvpi:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 5)


def compute_fund_valuation(db: Session, fund: Fund, as_of: date | None = None) -> ValuationResult:
    as_of = as_of or date.today()
    quarters = quarter_ends(fund.vintage_year, as_of)
    if len(quarters) < 2:
        quarters = quarter_ends(fund.vintage_year, date(fund.vintage_year, 12, 31))
    q_returns = _blended_quarterly_returns(db, fund, quarters)

    result = ValuationResult()
    calibrated = _calibrate_alpha(fund, quarters, q_returns)
    if calibrated is not None:
        result.alpha_annual = calibrated
        result.confidence = "high"
    else:
        track_alpha = _track_record_alpha(db, fund.provider_id)
        if track_alpha is not None:
            result.alpha_annual = track_alpha
            result.confidence = "medium"
        else:
            result.alpha_annual = 0.0
            result.confidence = "low"

    result.quarters = _simulate(fund, quarters, q_returns, result.alpha_annual)
    result.est_net_irr = _net_irr(result.quarters)
    result.pme_alpha = _pme_alpha(result.quarters)
    return result
