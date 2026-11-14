from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    # Keys are optional: in the cloud dev environment a network proxy adds the
    # Seats.aero header itself. SerpApi only accepts the key as a URL parameter,
    # so SERPAPI_KEY must be set wherever cash searches run.
    seats_aero_key: str | None
    serpapi_key: str | None
    cache_path: str
    static_dir: Path
    seats_aero_base: str = "https://seats.aero/partnerapi"
    serpapi_url: str = "https://serpapi.com/search.json"


def load_settings() -> Settings:
    return Settings(
        seats_aero_key=os.environ.get("SEATS_AERO_KEY") or None,
        serpapi_key=os.environ.get("SERPAPI_KEY") or None,
        cache_path=os.environ.get("CACHE_PATH", str(BACKEND_DIR / "cache.sqlite3")),
        static_dir=Path(os.environ.get("STATIC_DIR", REPO_DIR / "static")),
    )
