"""Curated flagship fund families for each provider (~150 funds).

All vintages, sizes and reported marks are indicative estimates compiled from
public sources — GP press releases, fundraising coverage, and public pension
LP disclosures. Reported marks (`reported`) are deliberately round ballparks;
they calibrate the valuation model, which then rolls the estimate forward on
public benchmark returns. Nothing here is GP-confirmed data.
"""

from datetime import date

PENSION = "Public pension LP disclosures (indicative)"
PRESS = "GP/press reports (indicative)"

Q3_25 = date(2025, 9, 30)
Q4_24 = date(2024, 12, 31)

# Exposure shorthands (weights sum to 1.0, tags reference services/benchmarks.py)
DIV_BUYOUT = {"diversified_buyout": 0.6, "industrials": 0.2, "consumer": 0.2}
EURO_BUYOUT = {"diversified_buyout": 0.45, "industrials": 0.3, "consumer": 0.25}
SVCS_BUYOUT = {"diversified_buyout": 0.5, "industrials": 0.25, "financial_services": 0.25}
SOFTWARE = {"software": 1.0}
TECH_BUYOUT = {"software": 0.7, "diversified_buyout": 0.3}
GROWTH = {"growth_equity": 0.7, "software": 0.3}
VENTURE = {"growth_equity": 1.0}
HC_TILT = {"healthcare": 0.5, "diversified_buyout": 0.3, "software": 0.2}
CONSUMER_BUYOUT = {"consumer": 0.6, "healthcare": 0.2, "diversified_buyout": 0.2}
INFRA = {"energy_infrastructure": 1.0}
DIGITAL_INFRA = {"energy_infrastructure": 0.55, "real_estate": 0.45}
RENEWABLES = {"energy_infrastructure": 0.85, "industrials": 0.15}
REAL_ESTATE = {"real_estate": 1.0}
CREDIT = {"leveraged_credit": 1.0}
OPP_CREDIT = {"leveraged_credit": 0.8, "diversified_buyout": 0.2}
GP_STAKES = {"financial_services": 0.7, "diversified_buyout": 0.3}


def _f(provider, name, vintage, size, asset_class, strategy, exposures, reported=None, status=None):
    return {
        "provider": provider,
        "name": name,
        "vintage_year": vintage,
        "fund_size_musd": size,
        "asset_class": asset_class,
        "strategy": strategy,
        "exposures": exposures,
        "reported": reported,
        "status": status,
    }


def _mark(tvpi, as_of=Q3_25, irr=None, source=PENSION):
    return {"tvpi": tvpi, "irr": irr, "as_of": as_of, "source": source}


FUNDS: list[dict] = [
    # ---------------- PE buyout / growth ----------------
    _f("blackstone", "Blackstone Capital Partners VI", 2011, 15200, "pe_buyout", "Global large-cap buyout", DIV_BUYOUT, _mark(2.0, Q4_24, 0.13)),
    _f("blackstone", "Blackstone Capital Partners VII", 2016, 18000, "pe_buyout", "Global large-cap buyout", DIV_BUYOUT, _mark(1.85, Q3_25, 0.15)),
    _f("blackstone", "Blackstone Capital Partners VIII", 2019, 26200, "pe_buyout", "Global large-cap buyout", DIV_BUYOUT, _mark(1.35)),
    _f("blackstone", "Blackstone Capital Partners IX", 2022, 21000, "pe_buyout", "Global large-cap buyout", DIV_BUYOUT),
    _f("blackstone", "Blackstone Real Estate Partners IX", 2019, 20500, "real_assets", "Global opportunistic real estate", REAL_ESTATE, _mark(1.3)),
    _f("kkr", "KKR North America Fund XI", 2012, 8700, "pe_buyout", "North America buyout", DIV_BUYOUT, _mark(2.1, Q4_24, 0.16)),
    _f("kkr", "KKR Americas Fund XII", 2017, 13900, "pe_buyout", "Americas buyout", DIV_BUYOUT, _mark(1.7)),
    _f("kkr", "KKR North America Fund XIII", 2021, 19000, "pe_buyout", "North America buyout", DIV_BUYOUT, _mark(1.25)),
    _f("kkr", "KKR Global Infrastructure Investors IV", 2022, 17000, "real_assets", "Global core-plus infrastructure", INFRA),
    _f("apollo", "Apollo Investment Fund VIII", 2013, 18400, "pe_buyout", "Opportunistic buyout & distressed-for-control", SVCS_BUYOUT, _mark(1.55, Q4_24, 0.11)),
    _f("apollo", "Apollo Investment Fund IX", 2018, 24700, "pe_buyout", "Opportunistic buyout & distressed-for-control", SVCS_BUYOUT, _mark(1.5)),
    _f("apollo", "Apollo Investment Fund X", 2023, 20000, "pe_buyout", "Opportunistic buyout", SVCS_BUYOUT),
    _f("carlyle", "Carlyle Partners VI", 2013, 13000, "pe_buyout", "US large-cap buyout", DIV_BUYOUT, _mark(1.75, Q4_24, 0.12)),
    _f("carlyle", "Carlyle Partners VII", 2018, 18500, "pe_buyout", "US large-cap buyout", DIV_BUYOUT, _mark(1.45)),
    _f("carlyle", "Carlyle Partners VIII", 2021, 14800, "pe_buyout", "US large-cap buyout", DIV_BUYOUT),
    _f("tpg", "TPG Partners VII", 2015, 10500, "pe_buyout", "Global buyout", HC_TILT, _mark(1.9, Q3_25, 0.16)),
    _f("tpg", "TPG Partners VIII", 2019, 11500, "pe_buyout", "Global buyout", HC_TILT, _mark(1.5)),
    _f("tpg", "TPG Partners IX", 2022, 12000, "pe_buyout", "Global buyout", HC_TILT),
    _f("eqt", "EQT VIII", 2018, 12500, "pe_buyout", "European thematic buyout", EURO_BUYOUT, _mark(1.9)),
    _f("eqt", "EQT IX", 2021, 18400, "pe_buyout", "European thematic buyout", EURO_BUYOUT, _mark(1.3)),
    _f("eqt", "EQT X", 2023, 24000, "pe_buyout", "European thematic buyout", EURO_BUYOUT),
    _f("eqt", "EQT Infrastructure V", 2021, 18600, "real_assets", "Value-add infrastructure", INFRA, _mark(1.2)),
    _f("advent", "Advent GPE VIII", 2016, 13000, "pe_buyout", "Global sector buyout", SVCS_BUYOUT, _mark(1.9, Q3_25, 0.17)),
    _f("advent", "Advent GPE IX", 2019, 17500, "pe_buyout", "Global sector buyout", SVCS_BUYOUT, _mark(1.5)),
    _f("advent", "Advent GPE X", 2022, 25000, "pe_buyout", "Global sector buyout", SVCS_BUYOUT),
    _f("vista", "Vista Equity Partners Fund VI", 2016, 11000, "pe_buyout", "Enterprise software buyout", SOFTWARE, _mark(1.6, Q3_25, 0.11)),
    _f("vista", "Vista Equity Partners Fund VII", 2019, 16000, "pe_buyout", "Enterprise software buyout", SOFTWARE, _mark(1.35)),
    _f("vista", "Vista Equity Partners Fund VIII", 2023, 20000, "pe_buyout", "Enterprise software buyout", SOFTWARE),
    _f("thoma-bravo", "Thoma Bravo Fund XIII", 2019, 12600, "pe_buyout", "Software & cybersecurity buyout", SOFTWARE, _mark(1.6)),
    _f("thoma-bravo", "Thoma Bravo Fund XIV", 2021, 17800, "pe_buyout", "Software & cybersecurity buyout", SOFTWARE, _mark(1.2)),
    _f("thoma-bravo", "Thoma Bravo Fund XV", 2023, 24300, "pe_buyout", "Software & cybersecurity buyout", SOFTWARE),
    _f("silver-lake", "Silver Lake Partners V", 2017, 15000, "pe_buyout", "Large-cap technology", TECH_BUYOUT, _mark(1.7, Q3_25, 0.14)),
    _f("silver-lake", "Silver Lake Partners VI", 2020, 20000, "pe_buyout", "Large-cap technology", TECH_BUYOUT, _mark(1.3)),
    _f("silver-lake", "Silver Lake Partners VII", 2024, 20500, "pe_buyout", "Large-cap technology", TECH_BUYOUT),
    _f("cvc", "CVC Capital Partners VII", 2017, 18000, "pe_buyout", "European large-cap buyout", EURO_BUYOUT, _mark(1.6)),
    _f("cvc", "CVC Capital Partners VIII", 2020, 23000, "pe_buyout", "European large-cap buyout", EURO_BUYOUT, _mark(1.3)),
    _f("cvc", "CVC Capital Partners IX", 2023, 28000, "pe_buyout", "European large-cap buyout", EURO_BUYOUT),
    _f("warburg-pincus", "Warburg Pincus Private Equity XII", 2015, 13400, "pe_buyout", "Global growth buyout", GROWTH, _mark(1.8, Q3_25, 0.14)),
    _f("warburg-pincus", "Warburg Pincus Global Growth", 2018, 14800, "pe_buyout", "Global growth buyout", GROWTH, _mark(1.5)),
    _f("warburg-pincus", "Warburg Pincus Global Growth 14", 2023, 17300, "pe_buyout", "Global growth buyout", GROWTH),
    _f("bain-capital", "Bain Capital Fund XII", 2017, 9400, "pe_buyout", "Global buyout", DIV_BUYOUT, _mark(1.65)),
    _f("bain-capital", "Bain Capital Fund XIII", 2021, 11800, "pe_buyout", "Global buyout", DIV_BUYOUT, _mark(1.2)),
    _f("bain-capital", "Bain Capital Europe V", 2019, 5800, "pe_buyout", "European buyout", EURO_BUYOUT, _mark(1.45)),
    _f("hellman-friedman", "Hellman & Friedman Capital Partners VIII", 2016, 11000, "pe_buyout", "Concentrated large-cap buyout", TECH_BUYOUT, _mark(1.9, Q3_25, 0.16)),
    _f("hellman-friedman", "Hellman & Friedman Capital Partners IX", 2018, 16500, "pe_buyout", "Concentrated large-cap buyout", TECH_BUYOUT, _mark(1.5)),
    _f("hellman-friedman", "Hellman & Friedman Capital Partners X", 2021, 24400, "pe_buyout", "Concentrated large-cap buyout", TECH_BUYOUT),
    _f("permira", "Permira VI", 2016, 8500, "pe_buyout", "European buyout", TECH_BUYOUT, _mark(1.8)),
    _f("permira", "Permira VII", 2019, 12700, "pe_buyout", "European buyout", TECH_BUYOUT, _mark(1.4)),
    _f("permira", "Permira VIII", 2023, 18400, "pe_buyout", "European buyout", TECH_BUYOUT),
    _f("cinven", "Sixth Cinven Fund", 2016, 8000, "pe_buyout", "European buyout", EURO_BUYOUT, _mark(1.75)),
    _f("cinven", "Seventh Cinven Fund", 2019, 11300, "pe_buyout", "European buyout", EURO_BUYOUT, _mark(1.4)),
    _f("cinven", "Eighth Cinven Fund", 2024, 14500, "pe_buyout", "European buyout", EURO_BUYOUT),
    _f("general-atlantic", "General Atlantic Investment Program 2017", 2017, 3300, "pe_buyout", "Global growth equity", GROWTH, _mark(1.9)),
    _f("general-atlantic", "General Atlantic Investment Program 2019", 2019, 5000, "pe_buyout", "Global growth equity", GROWTH, _mark(1.5)),
    _f("general-atlantic", "General Atlantic Investment Program 2021", 2021, 7800, "pe_buyout", "Global growth equity", GROWTH, _mark(1.15)),
    _f("insight-partners", "Insight Partners X", 2018, 6300, "pe_buyout", "Software ScaleUp growth", SOFTWARE, _mark(1.7)),
    _f("insight-partners", "Insight Partners XI", 2020, 9500, "pe_buyout", "Software ScaleUp growth", SOFTWARE, _mark(1.25)),
    _f("insight-partners", "Insight Partners XII", 2022, 20000, "pe_buyout", "Software ScaleUp growth", SOFTWARE),
    _f("cdr", "Clayton, Dubilier & Rice Fund X", 2017, 10000, "pe_buyout", "Operational buyout", SVCS_BUYOUT, _mark(1.8, Q3_25, 0.15)),
    _f("cdr", "Clayton, Dubilier & Rice Fund XI", 2021, 16000, "pe_buyout", "Operational buyout", SVCS_BUYOUT, _mark(1.2)),
    _f("cdr", "Clayton, Dubilier & Rice Fund XII", 2023, 26000, "pe_buyout", "Operational buyout", SVCS_BUYOUT),
    _f("leonard-green", "Green Equity Investors VII", 2016, 9600, "pe_buyout", "Consumer & services buyout", CONSUMER_BUYOUT, _mark(1.7)),
    _f("leonard-green", "Green Equity Investors VIII", 2019, 12000, "pe_buyout", "Consumer & services buyout", CONSUMER_BUYOUT, _mark(1.4)),
    _f("leonard-green", "Green Equity Investors IX", 2023, 14000, "pe_buyout", "Consumer & services buyout", CONSUMER_BUYOUT),
    # ---------------- Venture capital ----------------
    _f("sequoia", "Sequoia Capital US Venture Fund XV", 2016, 900, "vc", "US early-stage venture", VENTURE, _mark(3.0, Q4_24, source=PRESS)),
    _f("sequoia", "Sequoia Capital US Growth Fund IX", 2020, 7200, "vc", "US growth", GROWTH, _mark(1.4, source=PRESS)),
    _f("sequoia", "Sequoia Capital US Venture Fund XVII", 2022, 1100, "vc", "US early-stage venture", VENTURE),
    _f("a16z", "a16z Fund V", 2016, 1500, "vc", "Multi-stage venture", VENTURE, _mark(2.5, Q4_24, source=PRESS)),
    _f("a16z", "a16z Fund VI", 2019, 2750, "vc", "Multi-stage venture", VENTURE, _mark(1.8, source=PRESS)),
    _f("a16z", "a16z Growth Fund III", 2022, 5000, "vc", "Late-stage growth", GROWTH),
    _f("accel", "Accel XIII", 2016, 500, "vc", "Early-stage venture", VENTURE, _mark(3.0, Q4_24, source=PRESS)),
    _f("accel", "Accel XIV", 2019, 525, "vc", "Early-stage venture", VENTURE, _mark(2.0, source=PRESS)),
    _f("accel", "Accel Growth Fund V", 2021, 1750, "vc", "Growth-stage venture", GROWTH, _mark(1.2, source=PRESS)),
    _f("lightspeed", "Lightspeed Venture Partners XII", 2018, 750, "vc", "Early-stage venture", VENTURE, _mark(2.0, source=PRESS)),
    _f("lightspeed", "Lightspeed Venture Partners XIII", 2020, 890, "vc", "Early-stage venture", VENTURE, _mark(1.4, source=PRESS)),
    _f("lightspeed", "Lightspeed Venture Partners XIV", 2022, 1980, "vc", "Multi-stage venture", VENTURE),
    _f("index-ventures", "Index Ventures IX", 2018, 650, "vc", "Early-stage venture", VENTURE, _mark(2.2, source=PRESS)),
    _f("index-ventures", "Index Ventures X", 2020, 800, "vc", "Early-stage venture", VENTURE, _mark(1.5, source=PRESS)),
    _f("index-ventures", "Index Ventures Growth V", 2021, 2000, "vc", "Growth-stage venture", GROWTH),
    _f("founders-fund", "Founders Fund VI", 2016, 1300, "vc", "Concentrated frontier tech", VENTURE, _mark(3.0, Q4_24, source=PRESS)),
    _f("founders-fund", "Founders Fund VII", 2019, 1500, "vc", "Concentrated frontier tech", VENTURE, _mark(2.0, source=PRESS)),
    _f("founders-fund", "Founders Fund VIII", 2022, 1900, "vc", "Concentrated frontier tech", VENTURE),
    _f("nea", "NEA 15", 2015, 2800, "vc", "Multi-stage tech & healthcare", VENTURE, _mark(1.9, Q4_24)),
    _f("nea", "NEA 16", 2017, 3300, "vc", "Multi-stage tech & healthcare", VENTURE, _mark(1.7)),
    _f("nea", "NEA 17", 2019, 3600, "vc", "Multi-stage tech & healthcare", VENTURE, _mark(1.4)),
    _f("nea", "NEA 18", 2022, 6200, "vc", "Multi-stage tech & healthcare", VENTURE),
    _f("bessemer", "Bessemer Venture Partners IX", 2015, 1600, "vc", "Cloud-focused venture", VENTURE, _mark(2.2, Q4_24)),
    _f("bessemer", "Bessemer Venture Partners X", 2018, 1850, "vc", "Cloud-focused venture", VENTURE, _mark(1.7)),
    _f("bessemer", "Bessemer Venture Partners XI", 2021, 2475, "vc", "Cloud-focused venture", VENTURE),
    _f("general-catalyst", "General Catalyst Group VIII", 2016, 845, "vc", "Multi-stage venture", VENTURE, _mark(2.4, Q4_24, source=PRESS)),
    _f("general-catalyst", "General Catalyst Group IX", 2018, 1375, "vc", "Multi-stage venture", VENTURE, _mark(1.8, source=PRESS)),
    _f("general-catalyst", "General Catalyst Group XI", 2021, 4600, "vc", "Multi-stage venture", VENTURE),
    _f("khosla", "Khosla Ventures V", 2014, 1000, "vc", "Deep-tech venture", VENTURE, _mark(2.8, Q4_24, source=PRESS)),
    _f("khosla", "Khosla Ventures VI", 2018, 1400, "vc", "Deep-tech venture", VENTURE, _mark(1.9, source=PRESS)),
    _f("khosla", "Khosla Ventures VIII", 2023, 3000, "vc", "Deep-tech & AI venture", VENTURE),
    _f("greylock", "Greylock 15", 2016, 1000, "vc", "Early-stage enterprise", VENTURE, _mark(2.0, Q4_24, source=PRESS)),
    _f("greylock", "Greylock 16", 2019, 1000, "vc", "Early-stage enterprise", VENTURE, _mark(1.6, source=PRESS)),
    _f("greylock", "Greylock 17", 2021, 1600, "vc", "Early-stage enterprise & AI", VENTURE),
    _f("tiger-global", "Tiger Global PIP XII", 2019, 3750, "vc", "Late-stage crossover", GROWTH, _mark(1.3, source=PRESS)),
    _f("tiger-global", "Tiger Global PIP XIV", 2021, 12700, "vc", "Late-stage crossover", GROWTH, _mark(0.8, source=PRESS)),
    _f("tiger-global", "Tiger Global PIP XV", 2023, 2200, "vc", "Late-stage crossover", GROWTH),
    # ---------------- Real assets & infrastructure ----------------
    _f("brookfield", "Brookfield Infrastructure Fund III", 2016, 14000, "real_assets", "Global core-plus infrastructure", INFRA, _mark(1.6, Q3_25, 0.12)),
    _f("brookfield", "Brookfield Infrastructure Fund IV", 2019, 20000, "real_assets", "Global core-plus infrastructure", INFRA, _mark(1.35)),
    _f("brookfield", "Brookfield Infrastructure Fund V", 2023, 28000, "real_assets", "Global core-plus infrastructure", INFRA),
    _f("brookfield", "Brookfield Global Transition Fund", 2022, 15000, "real_assets", "Energy transition", RENEWABLES),
    _f("gip", "Global Infrastructure Partners III", 2016, 15800, "real_assets", "Large-cap infrastructure", INFRA, _mark(1.7, Q3_25, 0.13)),
    _f("gip", "Global Infrastructure Partners IV", 2019, 22000, "real_assets", "Large-cap infrastructure", INFRA, _mark(1.3)),
    _f("gip", "Global Infrastructure Partners V", 2023, 25000, "real_assets", "Large-cap infrastructure", INFRA),
    _f("stonepeak", "Stonepeak Infrastructure Fund II", 2016, 3500, "real_assets", "North America infrastructure", DIGITAL_INFRA, _mark(1.8, Q3_25, 0.14)),
    _f("stonepeak", "Stonepeak Infrastructure Fund III", 2018, 7200, "real_assets", "North America infrastructure", DIGITAL_INFRA, _mark(1.5)),
    _f("stonepeak", "Stonepeak Infrastructure Fund IV", 2021, 14000, "real_assets", "Global infrastructure", DIGITAL_INFRA, _mark(1.15)),
    _f("macquarie", "Macquarie European Infrastructure Fund 6", 2021, 9100, "real_assets", "European infrastructure", INFRA, _mark(1.2)),
    _f("macquarie", "Macquarie Infrastructure Partners IV", 2018, 5000, "real_assets", "Americas infrastructure", INFRA, _mark(1.4)),
    _f("macquarie", "Macquarie Infrastructure Partners V", 2021, 6900, "real_assets", "Americas infrastructure", INFRA),
    _f("digitalbridge", "DigitalBridge Partners I", 2018, 4100, "real_assets", "Digital infrastructure", DIGITAL_INFRA, _mark(1.5)),
    _f("digitalbridge", "DigitalBridge Partners II", 2021, 8300, "real_assets", "Digital infrastructure", DIGITAL_INFRA, _mark(1.15)),
    _f("digitalbridge", "DigitalBridge Partners III", 2023, 6000, "real_assets", "Digital infrastructure", DIGITAL_INFRA),
    _f("starwood", "Starwood Opportunity Fund X", 2015, 5600, "real_assets", "Opportunistic real estate", REAL_ESTATE, _mark(1.6, Q4_24)),
    _f("starwood", "Starwood Opportunity Fund XI", 2018, 7600, "real_assets", "Opportunistic real estate", REAL_ESTATE, _mark(1.4)),
    _f("starwood", "Starwood Opportunity Fund XII", 2021, 10000, "real_assets", "Opportunistic real estate", REAL_ESTATE, _mark(1.15)),
    _f("i-squared", "ISQ Global Infrastructure Fund I", 2015, 3000, "real_assets", "Global mid-cap infrastructure", INFRA, _mark(1.7, Q4_24)),
    _f("i-squared", "ISQ Global Infrastructure Fund II", 2018, 7000, "real_assets", "Global mid-cap infrastructure", INFRA, _mark(1.4)),
    _f("i-squared", "ISQ Global Infrastructure Fund III", 2022, 15000, "real_assets", "Global infrastructure", INFRA),
    _f("antin", "Antin Infrastructure Partners III", 2016, 4000, "real_assets", "European infrastructure", INFRA, _mark(1.6)),
    _f("antin", "Antin Infrastructure Partners IV", 2019, 7300, "real_assets", "European infrastructure", INFRA, _mark(1.3)),
    _f("antin", "Antin Infrastructure Partners V", 2022, 8900, "real_assets", "European infrastructure", INFRA),
    _f("cip", "Copenhagen Infrastructure III", 2018, 4900, "real_assets", "Greenfield renewables", RENEWABLES, _mark(1.3)),
    _f("cip", "Copenhagen Infrastructure IV", 2021, 8000, "real_assets", "Greenfield renewables", RENEWABLES, _mark(1.1)),
    _f("cip", "Copenhagen Infrastructure V", 2024, 13000, "real_assets", "Greenfield renewables", RENEWABLES),
    # ---------------- Private credit ----------------
    _f("oaktree", "Oaktree Opportunities Fund Xb", 2018, 8900, "private_credit", "Distressed & opportunistic credit", OPP_CREDIT, _mark(1.4)),
    _f("oaktree", "Oaktree Opportunities Fund XI", 2021, 16000, "private_credit", "Distressed & opportunistic credit", OPP_CREDIT, _mark(1.2)),
    _f("oaktree", "Oaktree Opportunities Fund XII", 2024, 16000, "private_credit", "Distressed & opportunistic credit", OPP_CREDIT),
    _f("hps", "HPS Specialty Loan Fund IV", 2018, 6500, "private_credit", "Senior direct lending", CREDIT, _mark(1.3)),
    _f("hps", "HPS Strategic Investment Partners IV", 2019, 9000, "private_credit", "Junior capital / mezzanine", CREDIT, _mark(1.35)),
    _f("hps", "HPS Specialty Loan Fund V", 2022, 17000, "private_credit", "Senior direct lending", CREDIT),
    _f("blue-owl", "Dyal Capital Partners III", 2015, 5300, "private_credit", "GP minority stakes", GP_STAKES, _mark(1.9, Q3_25, 0.13)),
    _f("blue-owl", "Dyal Capital Partners IV", 2019, 9000, "private_credit", "GP minority stakes", GP_STAKES, _mark(1.45)),
    _f("blue-owl", "Dyal Capital Partners V", 2021, 12900, "private_credit", "GP minority stakes", GP_STAKES, _mark(1.15)),
    _f("ares", "Ares Capital Europe IV", 2018, 7800, "private_credit", "European direct lending", CREDIT, _mark(1.3)),
    _f("ares", "Ares Capital Europe V", 2021, 12000, "private_credit", "European direct lending", CREDIT, _mark(1.15)),
    _f("ares", "Ares Senior Direct Lending Fund II", 2021, 8000, "private_credit", "US senior direct lending", CREDIT, _mark(1.15)),
    _f("ares", "Ares Special Opportunities Fund II", 2021, 7100, "private_credit", "Opportunistic credit", OPP_CREDIT),
    _f("sixth-street", "Sixth Street Opportunities Partners IV", 2019, 4000, "private_credit", "Opportunistic credit", OPP_CREDIT, _mark(1.35)),
    _f("sixth-street", "Sixth Street Growth Partners II", 2021, 4400, "private_credit", "Structured growth lending", {"leveraged_credit": 0.6, "growth_equity": 0.4}),
    _f("sixth-street", "Sixth Street Lending Partners", 2023, 15000, "private_credit", "US senior direct lending", CREDIT),
    _f("golub", "Golub Capital Partners 11", 2018, 2500, "private_credit", "Middle-market direct lending", CREDIT, _mark(1.3, source=PRESS)),
    _f("golub", "Golub Capital Partners 12", 2021, 3000, "private_credit", "Middle-market direct lending", CREDIT, _mark(1.15, source=PRESS)),
    _f("golub", "Golub Capital Partners 14", 2024, 2000, "private_credit", "Middle-market direct lending", CREDIT),
    _f("fortress", "Fortress Credit Opportunities Fund IV", 2015, 5000, "private_credit", "Opportunistic credit", OPP_CREDIT, _mark(1.5, Q4_24)),
    _f("fortress", "Fortress Credit Opportunities Fund V", 2021, 6500, "private_credit", "Opportunistic credit", OPP_CREDIT, _mark(1.15)),
    _f("centerbridge", "Centerbridge Capital Partners III", 2014, 6000, "private_credit", "Hybrid credit & PE", OPP_CREDIT, _mark(1.6, Q4_24)),
    _f("centerbridge", "Centerbridge Special Credit Partners III", 2016, 3400, "private_credit", "Special situations credit", OPP_CREDIT, _mark(1.45)),
    _f("centerbridge", "Centerbridge Capital Partners IV", 2020, 3800, "private_credit", "Hybrid credit & PE", OPP_CREDIT, _mark(1.2)),
    _f("icg", "ICG Europe Fund VI", 2015, 3400, "private_credit", "European subordinated debt", CREDIT, _mark(1.6, Q4_24)),
    _f("icg", "ICG Europe Fund VII", 2018, 5400, "private_credit", "European subordinated debt", CREDIT, _mark(1.35)),
    _f("icg", "ICG Europe Fund VIII", 2022, 8800, "private_credit", "European subordinated debt", CREDIT),
]
