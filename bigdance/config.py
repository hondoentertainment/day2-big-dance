"""Defaults: blend weights, margin sigma, confidence multipliers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

try:
    load_dotenv()
except OSError:
    # e.g. .env ACL allows only interactive user; CI or another account may not read it
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ModelWeights:
    w_market: float = 0.55
    w_ratings: float = 0.45
    sigma_game: float = 11.5
    home_court_points: float = 3.0
    efficiency_to_margin: float = 1.0
    p_blend_floor: float = 0.02
    p_blend_ceiling: float = 0.98
    books_full_weight_at: int = 5
    dispersion_coef: float = 0.25
    missing_ratings_multiplier: float = 0.75


WEIGHTS = ModelWeights()


def get_target_date() -> str:
    return os.environ.get("TARGET_DATE", "2026-03-20")


def get_timezone() -> str:
    return os.environ.get("TIMEZONE", "America/New_York")


def get_odds_api_key() -> str | None:
    key = os.environ.get("ODDS_API_KEY", "").strip()
    return key or None


def ratings_csv_path() -> Path:
    return PROJECT_ROOT / "data" / "team_ratings.csv"


def is_vercel() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


def runtime_data_dir() -> Path:
    """Writable directory for last_picks.json and runs/ (serverless FS is read-only except /tmp)."""
    if is_vercel():
        p = Path(os.environ.get("DATA_DIR", "/tmp/day2-bigdance"))
        p.mkdir(parents=True, exist_ok=True)
        (p / "runs").mkdir(exist_ok=True)
        return p
    p = PROJECT_ROOT / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def bundled_data_dir() -> Path:
    """Read-only bundled CSVs and examples (repo data/)."""
    return PROJECT_ROOT / "data"


def get_allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if raw == "*":
        return ["*"]
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://127.0.0.1:8000", "http://localhost:8000"]


def get_picks_cache_ttl_seconds() -> int:
    return max(0, int(os.environ.get("PICKS_CACHE_TTL_SECONDS", "180")))


def get_refresh_secret() -> str | None:
    s = os.environ.get("REFRESH_SECRET", "").strip()
    return s or None


def get_odds_min_interval_seconds() -> int:
    return max(0, int(os.environ.get("ODDS_MIN_INTERVAL_SECONDS", "45")))
