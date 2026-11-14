from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Program:
    name: str
    alliance: str | None
    url: str


# Seats.aero source id -> loyalty program. Transfer partners and point values
# per card come in a later step, once the user's cards are known.
PROGRAMS: dict[str, Program] = {
    "aeroplan": Program("Air Canada Aeroplan", "Star Alliance", "https://www.aircanada.com/aeroplan"),
    "united": Program("United MileagePlus", "Star Alliance", "https://www.united.com/en/us/book-flight/award"),
    "lufthansa": Program("Lufthansa Miles & More", "Star Alliance", "https://www.miles-and-more.com"),
    "turkish": Program("Turkish Miles&Smiles", "Star Alliance", "https://www.turkishairlines.com/en-int/miles-and-smiles/"),
    "singapore": Program("Singapore KrisFlyer", "Star Alliance", "https://www.singaporeair.com/en_UK/ppsclub-krisflyer/"),
    "azul": Program("Azul Fidelidade", None, "https://www.voeazul.com.br"),
    "american": Program("American AAdvantage", "oneworld", "https://www.aa.com/booking/find-flights?redeemMiles=true"),
    "alaska": Program("Alaska Atmos Rewards", "oneworld", "https://www.alaskaair.com"),
    "qantas": Program("Qantas Frequent Flyer", "oneworld", "https://www.qantas.com"),
    "qatar": Program("Qatar Privilege Club", "oneworld", "https://www.qatarairways.com/en/Privilege-Club.html"),
    "cathay": Program("Cathay Asia Miles", "oneworld", "https://www.cathaypacific.com"),
    "delta": Program("Delta SkyMiles", "SkyTeam", "https://www.delta.com"),
    "flyingblue": Program("Air France/KLM Flying Blue", "SkyTeam", "https://wwws.airfrance.us/search/advanced"),
    "virginatlantic": Program("Virgin Atlantic Flying Club", "SkyTeam", "https://www.virginatlantic.com"),
    "saudia": Program("Saudia AlFursan", "SkyTeam", "https://www.saudia.com/pages/loyalty-program"),
    "aeromexico": Program("Aeromexico Club Premier", "SkyTeam", "https://www.aeromexico.com"),
    "emirates": Program("Emirates Skywards", None, "https://www.emirates.com/english/skywards/"),
    "etihad": Program("Etihad Guest", None, "https://www.etihad.com/en/etihadguest"),
    "jetblue": Program("JetBlue TrueBlue", None, "https://www.jetblue.com"),
    "smiles": Program("GOL Smiles", None, "https://www.smiles.com.br"),
    "velocity": Program("Virgin Australia Velocity", None, "https://www.velocityfrequentflyer.com"),
    "eurobonus": Program("SAS EuroBonus", "SkyTeam", "https://www.flysas.com"),
    "connectmiles": Program("Copa ConnectMiles", "Star Alliance", "https://www.copaair.com"),
}


def program(source: str) -> Program:
    return PROGRAMS.get(source, Program(source, None, "https://seats.aero"))
