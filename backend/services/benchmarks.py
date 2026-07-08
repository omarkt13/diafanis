"""Benchmark basket definitions.

Each basket maps a sector tag (referenced by Fund.sector_exposures_json) to a
weighted set of liquid public tickers used to proxy that private-market
exposure. Weights are relative (normalized at computation time). ETFs carry
double weight so single-name idiosyncrasy doesn't dominate a basket.
"""

BASKETS: dict[str, dict] = {
    "software": {
        "name": "Enterprise Software & Technology",
        "tickers": {"MSFT": 1.0, "CRM": 1.0, "NOW": 1.0, "ADBE": 1.0, "ORCL": 1.0, "IGV": 2.0},
    },
    "healthcare_facilities": {
        "name": "Healthcare Facilities (REITs + Operators)",
        "tickers": {
            "WELL": 1.0, "VTR": 1.0, "OHI": 1.0, "DOC": 1.0,
            "HCA": 1.0, "UHS": 1.0, "EHC": 1.0, "ENSG": 1.0,
        },
    },
    "healthcare": {
        "name": "Healthcare & Life Sciences",
        "tickers": {"UNH": 1.0, "JNJ": 1.0, "TMO": 1.0, "ABBV": 1.0, "XLV": 2.0},
    },
    "consumer": {
        "name": "Consumer & Retail",
        "tickers": {"PG": 1.0, "KO": 1.0, "NKE": 1.0, "MCD": 1.0, "XLY": 2.0},
    },
    "industrials": {
        "name": "Industrials & Business Services",
        "tickers": {"HON": 1.0, "CAT": 1.0, "GE": 1.0, "UNP": 1.0, "XLI": 2.0},
    },
    "financial_services": {
        "name": "Financial Services",
        "tickers": {"JPM": 1.0, "BLK": 1.0, "SCHW": 1.0, "XLF": 2.0},
    },
    "energy_infrastructure": {
        "name": "Energy & Infrastructure",
        "tickers": {"BIP": 1.0, "AMT": 1.0, "NEE": 1.0, "ET": 1.0, "KMI": 1.0, "XLU": 2.0},
    },
    "real_estate": {
        "name": "Real Estate",
        "tickers": {"VNQ": 2.0, "PLD": 1.0, "EQIX": 1.0, "SPG": 1.0},
    },
    "leveraged_credit": {
        "name": "Leveraged Credit (BDCs + HY)",
        "tickers": {"ARCC": 1.0, "FSK": 1.0, "MAIN": 1.0, "HYG": 2.0, "BKLN": 1.0},
    },
    "growth_equity": {
        "name": "Growth Equity / Venture Proxy",
        "tickers": {"QQQ": 2.0, "ARKK": 1.0, "IPO": 1.0},
    },
    "diversified_buyout": {
        "name": "Diversified Large-Cap Buyout Proxy",
        "tickers": {"SPY": 2.0, "VTV": 1.0, "VB": 1.0},
    },
}


def all_tickers() -> set[str]:
    tickers: set[str] = set()
    for basket in BASKETS.values():
        tickers.update(basket["tickers"].keys())
    return tickers


def basket_name(sector_tag: str) -> str:
    basket = BASKETS.get(sector_tag)
    return basket["name"] if basket else sector_tag.replace("_", " ").title()
